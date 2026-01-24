"""Runner for executing stored Python scripts with policy guards."""

from __future__ import annotations

import importlib.abc
import ipaddress
import json
import socket
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

DISALLOWED_MODULES = {
    "sqlalchemy",
    "psycopg",
    "asyncpg",
    "pg8000",
    "pyodbc",
    "pymysql",
}
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
METADATA_HOSTS = {"169.254.169.254"}
DEFAULT_TIMEOUT_MS = 5000
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576


class BlockedImportFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any, target: Any = None):
        root = fullname.split(".")[0]
        if root in DISALLOWED_MODULES:
            raise ImportError(f"Import '{root}' is prohibited in script execution")
        return None


def _ensure_import_hook() -> None:
    if not any(isinstance(finder, BlockedImportFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, BlockedImportFinder())


@dataclass(frozen=True)
class RunnerConfig:
    allow_network: bool
    allowed_hosts: tuple[str, ...]
    blocked_private_ranges: bool
    max_response_bytes: int
    timeout_ms: int
    base_url: str
    executed_by: str | None
    policy: Dict[str, Any]


@dataclass
class ScriptHttpClient:
    config: RunnerConfig

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] | None = None,
        json_body: Any | None = None,
        timeout_ms: int | None = None,
        allow_local: bool = False,
    ) -> Dict[str, Any]:
        if not self.config.allow_network and not allow_local:
            raise RuntimeError("Network access is disabled for this script")
        parsed = urlparse(url)
        host = parsed.hostname
        if not allow_local:
            self._ensure_host_allowed(host)
        timeout_secs = (
            (timeout_ms if timeout_ms is not None else self.config.timeout_ms) / 1000
        ) or (DEFAULT_TIMEOUT_MS / 1000)
        with requests.request(
            method,
            url,
            headers=headers or {},
            json=json_body,
            timeout=timeout_secs,
            stream=True,
        ) as response:
            response.raise_for_status()
            payload = self._drain_response(response)
        return payload

    def _ensure_host_allowed(self, host: str | None) -> None:
        if not host:
            raise RuntimeError("Invalid host in script HTTP call")
        host_lower = host.lower()
        if self.config.allowed_hosts and host_lower not in self.config.allowed_hosts:
            raise RuntimeError("Host is not whitelisted for script HTTP calls")
        if self.config.blocked_private_ranges:
            self._ensure_not_private(host_lower)

    def _ensure_not_private(self, host: str) -> None:
        if host in METADATA_HOSTS:
            raise RuntimeError("Metadata endpoints are blocked during script execution")
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError as exc:
            raise RuntimeError("Unable to resolve host for script HTTP call") from exc
        for info in infos:
            addr_str = info[4][0]
            try:
                ip_addr = ipaddress.ip_address(addr_str)
            except ValueError:
                continue
            for network in PRIVATE_NETWORKS:
                if ip_addr in network:
                    raise RuntimeError(f"Private address not allowed: {ip_addr}")

    def _drain_response(self, response: requests.Response) -> Dict[str, Any]:
        content = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            content.extend(chunk)
            if len(content) > self.config.max_response_bytes:
                raise RuntimeError("Response exceeds the allowed byte limit")
        body = content.decode(response.encoding or "utf-8", errors="replace")
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }


@dataclass
class ScriptHttpFacade:
    client: ScriptHttpClient

    def get(
        self,
        url: str,
        headers: Dict[str, str] | None = None,
        timeout_ms: int | None = None,
    ) -> Dict[str, Any]:
        return self.client.request("GET", url, headers=headers, timeout_ms=timeout_ms)

    def post(
        self,
        url: str,
        headers: Dict[str, str] | None = None,
        json_body: Any | None = None,
        timeout_ms: int | None = None,
    ) -> Dict[str, Any]:
        return self.client.request(
            "POST", url, headers=headers, json_body=json_body, timeout_ms=timeout_ms
        )


@dataclass
class ScriptExecutionContext:
    config: RunnerConfig
    params: Dict[str, Any]
    input_data: Any | None
    logs: List[str] = field(default_factory=list)
    http_client: ScriptHttpClient = field(init=False)
    http: ScriptHttpFacade = field(init=False)
    start_time: float = field(default_factory=time.perf_counter)
    duration_ms: int = 0

    def __post_init__(self):
        self.http_client = ScriptHttpClient(self.config)
        self.http = ScriptHttpFacade(self.http_client)

    def log(self, message: str) -> None:
        text = str(message).strip()
        if text:
            self.logs.append(text)

    def call_sql_api(
        self,
        target: str,
        params: Dict[str, Any] | None = None,
        limit: int | None = None,
        timeout_ms: int | None = None,
    ) -> Dict[str, Any]:
        if target.startswith("/"):
            endpoint = self._normalize_runtime_endpoint(target)
            url = f"{self.config.base_url.rstrip('/')}{endpoint}"
        else:
            url = (
                f"{self.config.base_url.rstrip('/')}/api-manager/apis/{target}/execute"
            )
        payload = {"params": params or {}, "limit": limit}
        headers = {
            "Content-Type": "application/json",
            "X-Executed-By": self.config.executed_by or "script-runtime",
        }
        response = self.http_client.request(
            "POST",
            url,
            headers=headers,
            json_body=payload,
            timeout_ms=timeout_ms,
            allow_local=True,
        )
        parsed = json.loads(response["body"])
        if parsed.get("code") != 0:
            raise RuntimeError(parsed.get("message") or "SQL API call failed")
        return parsed.get("data", {}).get("result", {})

    def _normalize_runtime_endpoint(self, target: str) -> str:
        endpoint = target if target.startswith("/") else f"/{target.lstrip('/')}"
        if not endpoint.startswith("/runtime"):
            endpoint = f"/runtime{endpoint}"
        return endpoint

    def finalize_references(self) -> Dict[str, Any]:
        return {
            "params": self.params,
            "input": self.input_data,
            "policy_applied": self.config.policy,
        }


_context_holder: List[ScriptExecutionContext | None] = [None]


def _build_runner_config(payload: Dict[str, Any]) -> RunnerConfig:
    script_policy = payload.get("policy") or {}
    allow_network = bool(script_policy.get("allow_network"))
    allowed_hosts = tuple(
        host.lower()
        for host in script_policy.get("allowed_hosts", [])
        if isinstance(host, str) and host
    )
    blocked_private = bool(script_policy.get("blocked_private_ranges", True))
    max_bytes = int(
        script_policy.get("max_response_bytes") or DEFAULT_MAX_RESPONSE_BYTES
    )
    timeout_ms = int(payload.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
    base_url = payload.get("base_url")
    if not base_url:
        raise RuntimeError("Base URL is required for script execution")
    executed_by = payload.get("executed_by")
    return RunnerConfig(
        allow_network=allow_network,
        allowed_hosts=allowed_hosts,
        blocked_private_ranges=blocked_private,
        max_response_bytes=max_bytes,
        timeout_ms=timeout_ms,
        base_url=base_url,
        executed_by=executed_by,
        policy=script_policy,
    )


def _validate_output_size(output: Dict[str, Any], limit: int) -> None:
    serialized = json.dumps(output, ensure_ascii=False)
    if len(serialized.encode("utf-8")) > limit:
        raise RuntimeError("Script output exceeds the allowed byte limit")


def _read_payload() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw:
        raise RuntimeError("Empty payload supplied to script runner")
    return json.loads(raw)


def run_script(payload: Dict[str, Any]) -> Dict[str, Any]:
    script_text = payload.get("script")
    if not isinstance(script_text, str) or not script_text.strip():
        raise RuntimeError("Script body must be provided")
    params = dict(payload.get("params") or {})
    input_data = payload.get("input")
    runner_config = _build_runner_config(payload)
    context = ScriptExecutionContext(
        config=runner_config, params=params, input_data=input_data
    )
    _context_holder[0] = context
    namespace: Dict[str, Any] = {}
    exec(script_text, namespace)
    main_fn = namespace.get("main")
    if not callable(main_fn):
        raise RuntimeError("Script must define a callable main(params, input, ctx)")
    start = time.perf_counter()
    output = main_fn(params, input_data, context)
    duration_ms = int((time.perf_counter() - start) * 1000)
    context.duration_ms = duration_ms
    _validate_output_size(output, runner_config.max_response_bytes)
    return {
        "status": "success",
        "output": output,
        "duration_ms": duration_ms,
        "logs": context.logs,
        "references": context.finalize_references(),
    }


def main() -> None:
    _ensure_import_hook()
    try:
        payload = _read_payload()
        result = run_script(payload)
        print(json.dumps(result, ensure_ascii=False))
        _context_holder[0] = None
    except Exception as exc:
        context = _context_holder[0]
        error_payload: Dict[str, Any] = {
            "status": "error",
            "error": str(exc),
            "traceback": traceback.format_exc(limit=2),
        }
        if context:
            error_payload["logs"] = context.logs
            error_payload["references"] = context.finalize_references()
        print(json.dumps(error_payload, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
