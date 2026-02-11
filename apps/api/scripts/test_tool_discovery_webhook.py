#!/usr/bin/env python3
"""
Test script for runtime tool discovery webhook

This script demonstrates how to trigger tool discovery updates via webhook.
It can be used to test the webhook endpoint and verify that tools are
dynamically loaded without application restart.
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime

import requests

# API endpoint configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_URL = f"{BASE_URL}/ops/webhooks/tool-discovery"
STATUS_URL = f"{BASE_URL}/ops/tool-discovery/status"
REFRESH_URL = f"{BASE_URL}/ops/tool-discovery/refresh"

# Webhook secret (should match what's configured in the application)
WEBHOOK_SECRET = "your-webhook-secret-here"


def generate_webhook_signature(payload: dict) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    payload_str = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        WEBHOOK_secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def test_webhook():
    """Test the webhook endpoint."""
    print("🧪 Testing Tool Discovery Webhook...")

    # Create test payload
    payload = {
        "event": "tool_updated",
        "timestamp": datetime.now().isoformat(),
        "tool": {
            "name": "test_ci_search",
            "action": "created",
            "metadata": {
                "tool_type": "database_query",
                "category": "ci"
            }
        }
    }

    # Generate signature
    signature = generate_webhook_signature(payload)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}"
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            print("✅ Webhook test successful!")
        else:
            print("❌ Webhook test failed!")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")


async def test_discovery_status():
    """Test getting discovery status."""
    print("\n📊 Testing Discovery Status...")

    try:
        response = requests.get(STATUS_URL, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")


async def test_discovery_refresh():
    """Test manual refresh."""
    print("\n🔄 Testing Manual Refresh...")

    try:
        # Test without force
        response = requests.get(REFRESH_URL, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")


async def test_multiple_refreshes():
    """Test multiple refreshes in quick succession."""
    print("\n⚡ Testing Multiple Refreshes...")

    for i in range(3):
        print(f"\nRefresh #{i+1}")
        try:
            response = requests.get(f"{REFRESH_URL}?force=true", timeout=10)
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Changes: {data.get('changes_detected', 0)}")
            time.sleep(2)  # Wait between requests

        except Exception as e:
            print(f"Error: {str(e)}")


async def main():
    """Main test function."""
    print("🚀 Starting Tool Discovery Webhook Tests...")
    print("=" * 50)

    # Wait for server to be ready
    print("\n⏳ Waiting for server to be ready...")
    time.sleep(3)

    # Run tests
    await test_discovery_status()
    test_webhook()
    await test_discovery_refresh()
    await test_multiple_refreshes()

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())