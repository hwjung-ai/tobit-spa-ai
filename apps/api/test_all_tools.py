#!/usr/bin/env python3
"""Test all published tools and report results."""

import requests

BASE_URL = "http://localhost:8000"

def main():
    # Published tools 목록 가져오기
    resp = requests.get(f"{BASE_URL}/asset-registry/tools?status=published", timeout=10)
    tools_data = resp.json()["data"]["assets"]

    # 테스트 파라미터 매핑
    test_params = {
        "metric_list": {},
        "equipment_search": {"keyword": "test"},
        "production_status": {"status": "running"},
        "worker_schedule": {"date": "2026-02-17"},
        "maintenance_history": {"equipment_id": "test"},
        "bom_lookup": {"product_id": "test"},
        "energy_consumption": {"start_time": "2026-01-01T00:00:00Z", "end_time": "2026-02-17T00:00:00Z"},
        "event_aggregate": {},
        "metric_query": {"tenant_id": "default", "ci_code": "CI-001", "metric_name": "cpu_usage", "start_time": "2026-01-01T00:00:00Z", "end_time": "2026-02-17T00:00:00Z", "limit": 10},
        "metric_aggregate_by_ci": {"tenant_id": "default", "metric_name": "cpu_usage", "ci_ids": [], "function": "AVG", "start_time": "2026-01-01T00:00:00Z", "end_time": "2026-02-17T00:00:00Z"},
        "work_history_query": {"tenant_id": "default"},
        "maintenance_history_list": {"tenant_id": "default"},
        "maintenance_ticket_create": {"tenant_id": "default", "ci_id": "00000000-0000-0000-0000-000000000001", "maint_type": "Inspection", "summary": "test", "start_time": "2026-02-17T00:00:00Z", "performer": "test"},
        "history_combined_union": {"tenant_id": "default"},
        "ci_graph_query": {"tenant_id": "default", "relationship_types": ["depends"], "limit": 10},
        "ci_detail_lookup": {"field": "ci_code", "value": "CI-001", "tenant_id": "default"},
        "document_search": {"query": "test"},
    }

    print(f"{'tool_name':<30} {'tool_type':<15} {'work_or_not':<12} {'data_count':<10} {'error'}")
    print("-" * 120)

    for tool in tools_data:
        name = tool["name"]
        tool_type = tool.get("tool_type", "unknown")
        params = test_params.get(name, {})
        
        try:
            resp = requests.post(
                f"{BASE_URL}/asset-registry/tools/{name}/test",
                json=params,
                headers={"Content-Type": "application/json", "Authorization": "Bearer test"},
                timeout=10
            )
            data = resp.json()
            
            if data.get("code") == 0 and data.get("data", {}).get("success"):
                result_data = data["data"].get("data", {})
                rows = result_data.get("rows", [])
                count = len(rows) if isinstance(rows, list) else (1 if rows else 0)
                # Check for error_details even if success is true
                error_details = data["data"].get("error_details")
                if error_details:
                    print(f"{name:<30} {tool_type:<15} {'WARN':<12} {count:<10} {str(error_details)[:60]}")
                else:
                    print(f"{name:<30} {tool_type:<15} {'OK':<12} {count:<10}")
            else:
                error = data.get("data", {}).get("error", "Unknown error") if data.get("data") else data.get("message", "Unknown error")
                error_details = data.get("data", {}).get("error_details", "") if data.get("data") else ""
                print(f"{name:<30} {tool_type:<15} {'ERROR':<12} {'0':<10} {str(error)[:60]} {str(error_details)[:60]}")
        except Exception as e:
            print(f"{name:<30} {tool_type:<15} {'FAIL':<12} {'0':<10} {str(e)[:60]}")

if __name__ == "__main__":
    main()