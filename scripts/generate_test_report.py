from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _git_commit_hash() -> str:
    try:
        output = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        return output[:8]
    except Exception:
        return "unknown"


def _format_blocks(blocks: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        block_type = block.get("type")
        title = block.get("title") or block.get("label") or "<no title>"
        parts = [f"{block_type}"]
        if "rows" in block:
            parts.append(f"rows={block['rows']}")
        if "nodes" in block:
            parts.append(f"nodes={block['nodes']}")
        if "edges" in block:
            parts.append(f"edges={block['edges']}")
        lines.append(f"- `{title}` ({', '.join(parts)})")
    return lines


def _format_excerpt(title: str, excerpt: dict[str, Any]) -> list[str]:
    if not excerpt:
        return []
    return [f"- **{title}**: {', '.join(f'{k}={v}' for k, v in excerpt.items() if v is not None)}"]


def main() -> None:
    summary_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/ops_ci_api_summary.json")
    if not summary_path.exists():
        print(f"Summary file not found at {summary_path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    entries = data.get("entries", [])
    output_path = Path("TEST_REPORT.md")
    lines: list[str] = [
        "# OPS CI API Test Report",
        "",
        f"- **Generated at**: {datetime.utcnow().isoformat()}Z",
        f"- **Commit**: {metadata.get('git_commit', _git_commit_hash())}",
        f"- **Base URL**: {metadata.get('base_url', 'N/A')}",
        f"- **Endpoint**: {metadata.get('ci_endpoint', 'N/A')}",
        f"- **OPS_ASSUME_REAL_MODE**: {metadata.get('ops_assume_real_mode', 'true')}",
        f"- **CI code strategy**: {metadata.get('ci_code_strategy', 'seed')}",
        f"- **Seed range**: {metadata.get('seed_range', {}).get('from')} → {metadata.get('seed_range', {}).get('to')}",
        "",
        "## Summary",
        "",
        f"- Entry count: {len(entries)}",
        f"- Raw artifacts: {summary_path}",
        "",
    ]
    for entry in entries:
        status = entry.get("status", "unknown")
        lines.append(f"## {entry['test_name']} — `{status.upper()}`")
        lines.append(f"- **Query**: {entry['query']}")
        lines.append(f"- **Endpoint**: {entry['endpoint']}")
        if entry.get("reason"):
            lines.append(f"- **Reason**: {entry['reason']}")
        lines.append(f"- **Status code**: {entry.get('status_code')}")
        lines.extend(_format_excerpt("Meta", entry.get("meta_excerpt", {})))
        lines.extend(_format_excerpt("Trace", entry.get("trace_excerpt", {})))
        block_lines = _format_blocks(entry.get("blocks_summary", []))
        if block_lines:
            lines.append("- **Blocks**:")
            lines.extend(block_lines)
        lines.append(f"- **Raw response**: {entry.get('raw_response')}")
        if status != "pass":
            lines.append(f"- **Repro command**: `pytest tests/ops_ci_api/test_ops_ci_api.py -k {entry['test_name']}`")
        lines.append("")
    lines.append("## Re-run")
    lines.append("- `./scripts/run_ops_ci_api_tests.sh`")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
