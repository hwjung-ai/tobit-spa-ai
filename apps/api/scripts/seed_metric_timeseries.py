#!/usr/bin/env python3
"""
Seed metric timeseries data for simulation testing

Generates realistic metric timeseries data for sample services.
Usage:
    python scripts/seed_metric_timeseries.py
"""
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_session_context
from sqlalchemy import text
import random


SERVICES = [
    "api-gateway",
    "order-service",
    "payment-service",
    "user-service",
    "inventory-service",
]

METRICS = {
    "latency_ms": {"min": 20, "max": 150, "unit": "ms", "trend": "stable"},
    "throughput_rps": {"min": 50, "max": 300, "unit": "rps", "trend": "variable"},
    "error_rate_pct": {"min": 0.1, "max": 3.0, "unit": "%", "trend": "spiky"},
    "cost_usd_hour": {"min": 5, "max": 25, "unit": "USD/h", "trend": "stable"},
}


def _generate_value(metric_name: str, base_value: float, hour_offset: int) -> float:
    """Generate realistic metric value with trend and noise."""
    config = METRICS[metric_name]

    # Add trend variation
    if config["trend"] == "stable":
        noise = random.uniform(-0.1, 0.1) * base_value
    elif config["trend"] == "variable":
        noise = random.uniform(-0.3, 0.3) * base_value
    elif config["trend"] == "spiky":
        # Occasional spikes
        if random.random() < 0.1:
            noise = random.uniform(0.5, 1.5) * base_value
        else:
            noise = random.uniform(-0.1, 0.1) * base_value
    else:
        noise = 0

    value = base_value + noise
    value = max(config["min"], min(config["max"], value))
    return round(value, 3)


def _generate_timeseries_data(
    service: str, metric_name: str, hours_back: int = 168
) -> list[dict]:
    """Generate timeseries data points for a service metric."""
    config = METRICS[metric_name]
    base_value = (config["min"] + config["max"]) / 2

    data = []
    now = datetime.utcnow()

    for hour_offset in range(hours_back, 0, -1):
        timestamp = now - timedelta(hours=hour_offset)

        # Add time-of-day patterns
        hour_of_day = timestamp.hour
        if metric_name == "throughput_rps":
            # Higher during business hours
            if 9 <= hour_of_day <= 18:
                base_adjusted = base_value * 1.3
            else:
                base_adjusted = base_value * 0.7
        elif metric_name == "latency_ms":
            # Higher during peak hours
            if 12 <= hour_of_day <= 14 or 18 <= hour_of_day <= 20:
                base_adjusted = base_value * 1.2
            else:
                base_adjusted = base_value * 0.9
        else:
            base_adjusted = base_value

        value = _generate_value(metric_name, base_adjusted, hour_offset)

        data.append({
            "id": str(uuid4()),
            "tenant_id": "default",
            "service": service,
            "metric_name": metric_name,
            "timestamp": timestamp,
            "value": value,
            "unit": config["unit"],
            "tags": {"generated": "true", "test_data": "true"},
        })

    return data


def seed_metric_timeseries(
    tenant_id: str = "default",
    services: list[str] | None = None,
    hours_back: int = 168,
    batch_size: int = 1000,
) -> int:
    """
    Seed metric timeseries data for testing simulation.

    Args:
        tenant_id: Tenant identifier
        services: List of services to seed (default: all sample services)
        hours_back: How many hours of historical data to generate
        batch_size: Number of records per batch insert

    Returns:
        Total records inserted
    """
    if services is None:
        services = SERVICES

    total_inserted = 0

    with get_session_context() as session:
        # Check if table exists
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'tb_metric_timeseries'
            )
        """)
        exists = session.execute(check_table).scalar()

        if not exists:
            print("⚠️  Table tb_metric_timeseries does not exist. Run migration first.")
            print("   Run: python scripts/seed_metric_timeseries.py after migration")
            return 0

        print(f"Seeding metric timeseries data...")
        print(f"  Tenant: {tenant_id}")
        print(f"  Services: {', '.join(services)}")
        print(f"  Hours back: {hours_back}")
        print(f"  Metrics per service: {len(METRICS)}")

        # Clear existing test data for tenant
        clear_query = text("""
            DELETE FROM tb_metric_timeseries
            WHERE tenant_id = :tenant_id
            AND (tags->>'generated') = 'true'
        """)
        result = session.execute(clear_query, {"tenant_id": tenant_id})
        deleted = result.rowcount
        if deleted > 0:
            print(f"  Cleared {deleted} existing test records")

        # Generate and insert data
        for service in services:
            for metric_name in METRICS.keys():
                data_points = _generate_timeseries_data(
                    service, metric_name, hours_back
                )

                # Batch insert
                for i in range(0, len(data_points), batch_size):
                    batch = data_points[i:i + batch_size]

                    insert_query = text("""
                        INSERT INTO tb_metric_timeseries
                        (id, tenant_id, service, metric_name, timestamp, value, unit, tags, created_at)
                        VALUES
                    """ + ",".join([f"(:id_{j}, :tenant_id_{j}, :service_{j}, :metric_name_{j}, :timestamp_{j}, :value_{j}, :unit_{j}, :tags_{j}, NOW())" for j in range(len(batch))]))

                    params = {}
                    for j, row in enumerate(batch):
                        params[f"id_{j}"] = row["id"]
                        params[f"tenant_id_{j}"] = tenant_id
                        params[f"service_{j}"] = row["service"]
                        params[f"metric_name_{j}"] = row["metric_name"]
                        params[f"timestamp_{j}"] = row["timestamp"]
                        params[f"value_{j}"] = row["value"]
                        params[f"unit_{j}"] = row["unit"]
                        params[f"tags_{j}"] = row["tags"]

                    session.execute(insert_query, params)
                    total_inserted += len(batch)

                    if (total_inserted // batch_size) % 10 == 0:
                        print(f"  Inserted {total_inserted} records...")

        session.commit()

        # Print summary
        print(f"\n✅ Seeding complete!")
        print(f"   Total records inserted: {total_inserted}")
        print(f"   Services: {len(services)}")
        print(f"   Metrics per service: {len(METRICS)}")
        print(f"   Hours of data: {hours_back}")

        # Verify data
        verify_query = text("""
            SELECT
                service,
                metric_name,
                COUNT(*) as count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM tb_metric_timeseries
            WHERE tenant_id = :tenant_id
            AND (tags->>'generated') = 'true'
            GROUP BY service, metric_name
            ORDER BY service, metric_name
        """)
        results = session.execute(verify_query, {"tenant_id": tenant_id}).fetchall()

        print(f"\n📊 Data Summary:")
        print(f"   {'Service':<20} {'Metric':<20} {'Count':>8} {'Avg':>10} {'Min':>10} {'Max':>10}")
        print(f"   {'-'*20} {'-'*20} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
        for row in results:
            print(f"   {row[0]:<20} {row[1]:<20} {row[2]:>8} {row[3]:>10.2f} {row[4]:>10.2f} {row[5]:>10.2f}")

        return total_inserted


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Seed metric timeseries data")
    parser.add_argument("--tenant", default="default", help="Tenant ID")
    parser.add_argument("--services", nargs="*", help="Services to seed (default: all)")
    parser.add_argument("--hours", type=int, default=168, help="Hours of historical data")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("METRIC TIMESERIES DATA SEEDING")
    print("="*70)

    try:
        total = seed_metric_timeseries(
            tenant_id=args.tenant,
            services=args.services,
            hours_back=args.hours,
        )
        print("\n✅ Seeding complete!")
        return 0

    except Exception as e:
        print(f"\n❌ Seeding failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
