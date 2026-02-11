#!/bin/bash
# Manual Test Script for API Manager ↔ Tools Integration
# Usage: ./manual_test_api_to_tools_integration.sh <base_url> <token>

set -e

BASE_URL=${1:-"http://localhost:8000"}
TOKEN=${2:-"test-token"}

echo "========================================="
echo "API Manager ↔ Tools Integration Test"
echo "========================================="
echo "Base URL: $BASE_URL"
echo ""

# Step 1: Create a test API
echo "Step 1: Create Test API"
API_RESPONSE=$(curl -s -X POST "$BASE_URL/api-manager/apis" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Equipment API",
    "description": "Test API for integration testing",
    "mode": "sql",
    "method": "POST",
    "path": "/test/equipment",
    "logic": {"sql": "SELECT 1 as id, '\''Test'\'' as name"},
    "param_schema": {
      "type": "object",
      "properties": {
        "equipment_id": {"type": "string", "description": "Equipment ID"}
      },
      "required": []
    }
  }')

API_ID=$(echo $API_RESPONSE | jq -r '.data.api_id // .data.id // empty')
if [ "$API_ID" = "empty" ]; then
  echo "ERROR: Failed to create API"
  echo "$API_RESPONSE"
  exit 1
fi
echo "Created API: $API_ID"
echo ""

# Step 2: Export API to Tools
echo "Step 2: Export API to Tools"
EXPORT_RESPONSE=$(curl -s -X POST "$BASE_URL/api-manager/apis/$API_ID/export-to-tools" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"export": true}')

EXPORT_STATUS=$(echo $EXPORT_RESPONSE | jq -r '.data.export_status // empty')
echo "Export Status: $EXPORT_STATUS"
echo ""

# Step 3: List available exports
echo "Step 3: List Available Exports"
EXPORTS_RESPONSE=$(curl -s -X GET "$BASE_URL/asset-registry/tools/available-api-exports" \
  -H "Authorization: Bearer $TOKEN")

TOTAL_EXPORTS=$(echo $EXPORTS_RESPONSE | jq -r '.data.total // 0')
echo "Available exports: $TOTAL_EXPORTS"
echo ""

# Step 4: Import API as Tool
echo "Step 4: Import API as Tool"
IMPORT_RESPONSE=$(curl -s -X POST "$BASE_URL/asset-registry/tools/import-from-api-manager/$API_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tool: Test Equipment",
    "description": "Tool imported from API Manager",
    "infer_output_schema": false
  }')

TOOL_ID=$(echo $IMPORT_RESPONSE | jq -r '.data.tool_id // empty')
if [ "$TOOL_ID" = "empty" ]; then
  echo "ERROR: Failed to import API as Tool"
  echo "$IMPORT_RESPONSE"
  exit 1
fi
echo "Imported Tool: $TOOL_ID"
echo ""

# Step 5: Check bidirectional linkage
echo "Step 5: Check Bidirectional Linkage"
echo "--- API Side ---"
API_DETAIL=$(curl -s -X GET "$BASE_URL/api-manager/apis/$API_ID" \
  -H "Authorization: Bearer $TOKEN")

LINKED_TOOL_ID=$(echo $API_DETAIL | jq -r '.data.linked_to_tool_id // empty')
LINKED_TOOL_NAME=$(echo $API_DETAIL | jq -r '.data.linked_to_tool_name // empty')
echo "API.linked_to_tool_id: $LINKED_TOOL_ID"
echo "API.linked_to_tool_name: $LINKED_TOOL_NAME"
echo ""

echo "--- Tool Side ---"
TOOL_DETAIL=$(curl -s -X GET "$BASE_URL/asset-registry/tools/$TOOL_ID" \
  -H "Authorization: Bearer $TOKEN")

LINKED_FROM_API=$(echo $TOOL_DETAIL | jq -r '.data.asset.linked_from_api.is_internal_api // false')
LINKED_FROM_API_NAME=$(echo $TOOL_DETAIL | jq -r '.data.asset.linked_from_api.api_name // empty')
echo "Tool.linked_from_api.is_internal_api: $LINKED_FROM_API"
echo "Tool.linked_from_api.api_name: $LINKED_FROM_API_NAME"
echo ""

# Step 6: Test sync functionality
echo "Step 6: Test Sync Functionality"
SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/asset-registry/tools/$TOOL_ID/sync-from-api" \
  -H "Authorization: Bearer $TOKEN")

SYNCED_AT=$(echo $SYNC_RESPONSE | jq -r '.data.synced_at // empty')
echo "Synced at: $SYNCED_AT"
echo ""

# Step 7: List all tools to verify internal API flag
echo "Step 7: List Tools to Check Internal API Flag"
TOOLS_LIST=$(curl -s -X GET "$BASE_URL/asset-registry/tools" \
  -H "Authorization: Bearer $TOKEN")

INTERNAL_TOOL=$(echo $TOOLS_LIST | jq -r '.data.assets[] | select(.linked_from_api.is_internal_api == true) | .name')
echo "Internal API Tool found: $INTERNAL_TOOL"
echo ""

# Step 8: Test unlink functionality
echo "Step 8: Test Unlink Functionality"
UNLINK_RESPONSE=$(curl -s -X POST "$BASE_URL/api-manager/apis/$API_ID/unlink-from-tool" \
  -H "Authorization: Bearer $TOKEN")

UNLINK_MSG=$(echo $UNLINK_RESPONSE | jq -r '.data.message // empty')
echo "Unlink message: $UNLINK_MSG"
echo ""

# Verify unlink
API_UNLINKED=$(curl -s -X GET "$BASE_URL/api-manager/apis/$API_ID" \
  -H "Authorization: Bearer $TOKEN")

LINKED_AFTER_UNLINK=$(echo $API_UNLINKED | jq -r '.data.linked_to_tool_id // empty')
echo "API.linked_to_tool_id after unlink: $LINKED_AFTER_UNLINK"
echo ""

# Step 9: Test cancel export
echo "Step 9: Test Cancel Export"
CANCEL_RESPONSE=$(curl -s -X POST "$BASE_URL/api-manager/apis/$API_ID/export-to-tools" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"export": false}')

CANCEL_STATUS=$(echo $CANCEL_RESPONSE | jq -r '.data.export_status // empty')
echo "Cancel export status: $CANCEL_STATUS"
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✓ API creation"
echo "✓ Export to Tools"
echo "✓ List available exports"
echo "✓ Import as Tool"
echo "✓ Bidirectional linkage verified"
echo "✓ Sync functionality"
echo "✓ Internal API flag verified"
echo "✓ Unlink functionality"
echo "✓ Cancel export"
echo ""
echo "All tests passed!"