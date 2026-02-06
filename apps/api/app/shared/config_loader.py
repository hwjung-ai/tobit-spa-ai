from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# API root is 2 levels up from this file's location (apps/api/app/shared -> apps/api)
BASE_DIR = Path(__file__).resolve().parents[2]
RESOURCES_DIR = BASE_DIR / "resources"

_cache: Dict[str, Any] = {}
_mtime: Dict[str, float] = {}
_lock = Lock()
_observer = None


class _ResourceChangeHandler(FileSystemEventHandler):
    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        src_path = Path(event.src_path)
        try:
            relative_path = src_path.relative_to(RESOURCES_DIR).as_posix()
        except ValueError:
            return
        with _lock:
            if relative_path in _cache:
                logger.info(
                    "Resource file changed: %s. Invalidating cache.", relative_path
                )
                _cache.pop(relative_path, None)
                _mtime.pop(relative_path, None)


def _load_file(path: str, loader: Callable[[str], Any]) -> Any:
    """
    A generic file loader with mtime-based caching.
    `path` is relative to the `resources` directory under apps/api.
    """
    absolute_path = RESOURCES_DIR / path

    if not absolute_path.is_file():
        logger.error("Resource file not found: %s", absolute_path)
        return None

    current_mtime = absolute_path.stat().st_mtime

    with _lock:
        if path in _cache and _mtime.get(path) == current_mtime:
            return _cache[path]

        try:
            with open(absolute_path, "r", encoding="utf-8") as f:
                content = f.read()
                loaded_data = loader(content)
                _cache[path] = loaded_data
                _mtime[path] = current_mtime
                logger.info("Loaded and cached resource: %s", path)
                return loaded_data
        except Exception as e:
            logger.error("Failed to load or parse resource file %s: %s", path, e)
            return None


_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env_vars(content: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return os.environ.get(key, match.group(0))

    return _ENV_PATTERN.sub(_replace, content)


def load_yaml(path: str) -> Any:
    """
    Loads a YAML file from the resources directory under apps/api.
    The path should be relative to `resources/`.
    Example: `load_yaml("prompts/ci/planner.yaml")`
    """
    return _load_file(path, lambda content: yaml.safe_load(_expand_env_vars(content)))


def load_text(path: str) -> str | None:
    """
    Loads a text file (e.g., .sql, .cypher) from the resources directory under apps/api.
    The path should be relative to `resources/`.
    Example: `load_text("queries/postgres/ci/resolve_ci.sql")`
    """
    return _load_file(path, lambda content: content)


def start_watching(enable_watcher: bool = True):
    """
    Starts watching the resources directory for changes.
    """
    if not enable_watcher:
        logger.info("Resource file watcher is disabled.")
        return
    if not RESOURCES_DIR.exists():
        logger.warning("Resources directory not found: %s", RESOURCES_DIR)
        return

    global _observer
    if _observer:
        return  # Already running

    event_handler = _ResourceChangeHandler()
    _observer = Observer()
    _observer.schedule(event_handler, str(RESOURCES_DIR), recursive=True)
    _observer.start()
    logger.info("Started watching for changes in %s", RESOURCES_DIR)


def stop_watching():
    """
    Stops the file watcher.
    """
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        # Wait for thread to exit with timeout to avoid indefinite blocking
        try:
            _observer.join(timeout=2.0)
            if _observer.is_alive():
                logger.warning("Resource watcher thread did not stop within timeout")
        except Exception as e:
            logger.warning(f"Error while stopping resource watcher: {e}")
        _observer = None
        logger.info("Stopped resource file watcher.")
