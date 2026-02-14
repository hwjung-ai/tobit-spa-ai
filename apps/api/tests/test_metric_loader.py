#!/usr/bin/env python3
"""
Test metric loader functionality

Tests the metric loading from PostgreSQL timeseries table.
Usage:
    python tests/test_metric_loader.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.simulation.services.simulation.metric_loader import (
    _get_metric_timeseries,
    calculate_baseline_statistics,
    get_available_services_from_metrics,
    load_baseline_kpis,
)
from core.db import get_session_context


def test_get_available_services():
    """Test getting list of services with metric data."""
    print("\n" + "="*70)
    print("TEST: Get Available Services")
    print("="*70)

    try:
        with get_session_context() as session:
            services = get_available_services_from_metrics(tenant_id="default")

            if services:
                print(f"\n✅ Found {len(services)} services:")
                for service in services:
                    print(f"   - {service}")
            else:
                print("\n⚠️  No services found with metric data")

            return services is not None

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_baseline_kpis():
    """Test loading baseline KPIs for a service."""
    print("\n" + "="*70)
    print("TEST: Load Baseline KPIs")
    print("="*70)

    service = "api-gateway"

    try:
        baseline = load_baseline_kpis(
            tenant_id="default",
            service=service,
            hours_back=168
        )

        print(f"\n📊 Baseline KPIs for {service}:")
        print(f"   {'Metric':<25} {'Value':>15} {'Unit':<10}")
        print(f"   {'-'*25} {'-'*15} {'-'*10}")

        for metric_name, value in baseline.items():
            if metric_name not in ["_source", "_count"]:
                unit = _get_unit_for_metric(metric_name)
                print(f"   {metric_name:<25} {value:>15.2f} {unit:<10}")

        if baseline.get("_source") == "metrics":
            print("\n✅ Data source: metric_timeseries (PostgreSQL)")
            print(f"   Data points: {baseline.get('_count', 0)}")
        else:
            print(f"\n⚠️  Data source: {baseline.get('_source', 'unknown')}")
            print("   (Using fallback defaults)")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calculate_statistics():
    """Test baseline statistics calculation."""
    print("\n" + "="*70)
    print("TEST: Calculate Baseline Statistics")
    print("="*70)

    # Sample metric data
    sample_data = [
        {"timestamp": "2024-01-01 00:00:00", "value": 45.2},
        {"timestamp": "2024-01-01 01:00:00", "value": 47.8},
        {"timestamp": "2024-01-01 02:00:00", "value": 43.5},
        {"timestamp": "2024-01-01 03:00:00", "value": 52.1},
        {"timestamp": "2024-01-01 04:00:00", "value": 48.9},
    ]

    aggregations = ["mean", "median", "p95", "max", "min"]

    print(f"\n📈 Sample data ({len(sample_data)} points):")
    print(f"   Values: {[d['value'] for d in sample_data]}")

    print("\n📊 Statistics:")
    for agg in aggregations:
        result = calculate_baseline_statistics(sample_data, aggregation=agg)
        print(f"   {agg:<10}: {result:>10.2f}")

    return True


def test_metric_timeseries_query():
    """Test direct metric timeseries query."""
    print("\n" + "="*70)
    print("TEST: Metric Timeseries Query")
    print("="*70)

    try:
        with get_session_context() as session:
            metric_data = _get_metric_timeseries(
                session=session,
                tenant_id="default",
                service="api-gateway",
                metric_names=["latency_ms"],
                hours_back=24
            )

            print("\n📈 Metric timeseries data:")
            for metric_name, records in metric_data.items():
                print(f"\n   Metric: {metric_name}")
                print(f"   Records: {len(records)}")
                if records:
                    print("   Latest values:")
                    for record in records[-5:]:
                        print(f"     - {record['timestamp']}: {record['value']:.2f} {record.get('unit', '')}")

            return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _get_unit_for_metric(metric_name: str) -> str:
    """Get unit for metric name."""
    units = {
        "latency_ms": "ms",
        "throughput_rps": "rps",
        "error_rate_pct": "%",
        "cost_usd_hour": "USD/h",
    }
    return units.get(metric_name, "")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("METRIC LOADER TEST SUITE")
    print("="*70)

    results = {
        "Available Services": test_get_available_services(),
        "Baseline KPIs": test_load_baseline_kpis(),
        "Statistics": test_calculate_statistics(),
        "Timeseries Query": test_metric_timeseries_query(),
    }

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")

    total = len(results)
    passed = sum(1 for p in results.values() if p)
    print(f"\n  Total: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
