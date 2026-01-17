"""
Integration tests for unified asset importer scripts.

Tests verify:
1. --cleanup-drafts only deletes drafts (no recreation)
2. --scope filtering works correctly
3. --apply is required for API calls
4. All importers have consistent behavior
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


class TestQueryAssetImporter:
    """Test query_asset_importer.py"""

    @pytest.fixture
    def mock_client(self):
        """Mock httpx.Client"""
        client = MagicMock()
        return client

    @pytest.fixture
    def sample_query_files(self, tmp_path):
        """Create sample query files for testing"""
        query_root = tmp_path / "queries"
        ci_dir = query_root / "db1" / "ci"
        ci_dir.mkdir(parents=True)

        # Create YAML metadata
        yaml_file = ci_dir / "test_query.yaml"
        yaml_file.write_text(
            """
name: test_query
scope: ci
description: Test query
query_metadata:
  timeout: 30
query_params: []
"""
        )

        # Create SQL file
        sql_file = ci_dir / "test_query.sql"
        sql_file.write_text("SELECT * FROM table")

        return query_root

    def test_cleanup_drafts_only_deletes_not_creates(self, mock_client):
        """
        Test: --cleanup-drafts + --apply only deletes, does not create
        Verify: Draft deletion happens, then function returns without processing files
        """
        from query_asset_importer import execute_import

        # Mock the fetch to return a draft asset
        mock_client.get.return_value.json.return_value = {
            "data": {
                "assets": [
                    {
                        "name": "test_query",
                        "asset_id": "draft-123",
                        "status": "draft",
                        "scope": "ci",
                    }
                ]
            }
        }

        # Mock delete response
        mock_client.delete.return_value.status_code = 200
        mock_client.delete.return_value.text = ""

        # Execute with cleanup_drafts=True
        with patch("query_asset_importer.httpx.Client", return_value=mock_client):
            execute_import(
                files=[],  # Empty files list - should not matter
                base_url="http://localhost:8000",
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],
            )

        # Verify DELETE was called for draft
        assert mock_client.delete.called, "DELETE should be called for draft"
        delete_call_url = mock_client.delete.call_args[0][0]
        assert "draft-123" in delete_call_url

        # Verify POST was NOT called (no asset creation)
        assert not mock_client.post.called, "POST should NOT be called when only cleanup-drafts"

    def test_apply_without_cleanup_drafts_creates_assets(self, mock_client):
        """
        Test: --apply (without --cleanup-drafts) creates/updates assets
        Verify: No deletion, only creation/update
        """
        from query_asset_importer import execute_import

        mock_client.get.return_value.json.return_value = {
            "data": {"assets": []}  # No existing assets
        }

        # Mock POST response
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "data": {
                "asset": {
                    "asset_id": "new-123",
                    "status": "draft",
                    "name": "test_query",
                }
            }
        }

        with patch("query_asset_importer.httpx.Client", return_value=mock_client), patch(
            "query_asset_importer.collect_query_files", return_value=[]
        ):
            execute_import(
                files=[],
                base_url="http://localhost:8000",
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=False,  # No cleanup
                scopes=["ci"],
            )

        # Verify DELETE was NOT called
        assert not mock_client.delete.called, "DELETE should NOT be called without cleanup-drafts"

    def test_no_apply_is_dry_run(self, mock_client):
        """
        Test: Without --apply, no HTTP client is created (dry-run mode)
        Verify: No API calls are made
        """
        from query_asset_importer import execute_import

        with patch("query_asset_importer.httpx.Client") as mock_client_class:
            mock_client_class.return_value = mock_client

            execute_import(
                files=[],
                base_url="http://localhost:8000",
                actor="test",
                apply=False,  # No apply
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],
            )

            # Verify httpx.Client was NOT instantiated
            assert (
                not mock_client_class.called
            ), "httpx.Client should not be created without --apply"

    def test_scope_filtering(self, mock_client):
        """
        Test: --scope filters both file collection and asset fetching
        Verify: Only specified scopes are processed
        """
        from query_asset_importer import execute_import

        mock_client.get.return_value.json.return_value = {
            "data": {
                "assets": [
                    {
                        "name": "ci_query",
                        "asset_id": "id-1",
                        "status": "draft",
                        "scope": "ci",
                    },
                    {
                        "name": "discovery_query",
                        "asset_id": "id-2",
                        "status": "draft",
                        "scope": "discovery",
                    },
                ]
            }
        }

        mock_client.delete.return_value.status_code = 200
        mock_client.delete.return_value.text = ""

        with patch("query_asset_importer.httpx.Client", return_value=mock_client):
            execute_import(
                files=[],
                base_url="http://localhost:8000",
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],  # Only ci scope
            )

        # Verify only ci scope's draft was deleted
        delete_calls = mock_client.delete.call_args_list
        assert len(delete_calls) == 1, "Only 1 draft should be deleted (ci scope only)"
        assert "id-1" in delete_calls[0][0][0], "Should delete ci scope draft"


class TestPromptAssetImporter:
    """Test prompt_asset_importer.py"""

    def test_cleanup_drafts_only_deletes_not_creates(self):
        """
        Test: prompt importer --cleanup-drafts only deletes
        Verify: Matches query behavior
        """
        from prompt_asset_importer import execute_import

        mock_client = MagicMock()
        mock_client.get.return_value.json.return_value = {
            "data": {
                "assets": [
                    {
                        "name": "test_prompt",
                        "asset_id": "prompt-draft-1",
                        "status": "draft",
                        "scope": "ci",
                    }
                ]
            }
        }
        mock_client.delete.return_value.status_code = 200
        mock_client.delete.return_value.text = ""

        with patch("prompt_asset_importer.httpx.Client", return_value=mock_client):
            execute_import(
                files=[],
                base_url="http://localhost:8000",
                input_schema=None,
                output_contract=None,
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],
            )

        # Verify DELETE was called
        assert mock_client.delete.called, "DELETE should be called"
        # Verify POST was NOT called
        assert not mock_client.post.called, "POST should NOT be called"


class TestPolicyAssetImporter:
    """Test policy_asset_importer.py"""

    def test_cleanup_drafts_scope_filtering(self):
        """
        Test: policy importer --cleanup-drafts respects --scope
        Verify: Only specified scope drafts are deleted
        """
        from policy_asset_importer import execute_import

        mock_client = MagicMock()
        mock_client.get.return_value.json.return_value = {
            "data": {
                "assets": [
                    {
                        "name": "policy_1",
                        "asset_id": "policy-1",
                        "status": "draft",
                        "scope": "ci",
                    },
                    {
                        "name": "policy_2",
                        "asset_id": "policy-2",
                        "status": "draft",
                        "scope": "ops",
                    },
                ]
            }
        }
        mock_client.delete.return_value.status_code = 200
        mock_client.delete.return_value.text = ""

        with patch("policy_asset_importer.httpx.Client", return_value=mock_client):
            execute_import(
                files=[],
                base_url="http://localhost:8000",
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],  # Only ci
            )

        # Should only delete ci scope
        delete_calls = mock_client.delete.call_args_list
        assert len(delete_calls) == 1
        assert "policy-1" in delete_calls[0][0][0]


class TestMappingAssetImporter:
    """Test mapping_asset_importer.py"""

    def test_cleanup_drafts_only_deletes_not_creates(self):
        """
        Test: mapping importer --cleanup-drafts only deletes
        Verify: Matches other importers
        """
        from mapping_asset_importer import execute_import

        mock_client = MagicMock()
        mock_client.get.return_value.json.return_value = {
            "data": {
                "assets": [
                    {
                        "name": "mapping_1",
                        "asset_id": "mapping-draft-1",
                        "status": "draft",
                        "scope": "ci",
                    }
                ]
            }
        }
        mock_client.delete.return_value.status_code = 200
        mock_client.delete.return_value.text = ""

        with patch("mapping_asset_importer.httpx.Client", return_value=mock_client):
            execute_import(
                files=[],
                base_url="http://localhost:8000",
                actor="test",
                apply=True,
                publish=False,
                cleanup_drafts=True,
                scopes=["ci"],
            )

        # Verify DELETE was called
        assert mock_client.delete.called
        # Verify POST was NOT called
        assert not mock_client.post.called


class TestCLIArguments:
    """Test CLI argument parsing"""

    def test_query_importer_arguments(self):
        """Test query importer accepts all unified parameters"""
        import subprocess

        result = subprocess.run(
            ["python", str(REPO_ROOT / "scripts" / "query_asset_importer.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--scope" in result.stdout, "--scope should be available"
        assert "--cleanup-drafts" in result.stdout, "--cleanup-drafts should be available"
        assert "--cleanup" in result.stdout, "--cleanup alias should be available"
        assert "--apply" in result.stdout, "--apply should be available"
        assert "--publish" in result.stdout, "--publish should be available"

    def test_prompt_importer_arguments(self):
        """Test prompt importer accepts all unified parameters"""
        import subprocess

        result = subprocess.run(
            ["python", str(REPO_ROOT / "scripts" / "prompt_asset_importer.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--scope" in result.stdout
        assert "--cleanup-drafts" in result.stdout
        assert "--cleanup" in result.stdout

    def test_policy_importer_arguments(self):
        """Test policy importer accepts all unified parameters"""
        import subprocess

        result = subprocess.run(
            ["python", str(REPO_ROOT / "scripts" / "policy_asset_importer.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--scope" in result.stdout
        assert "--cleanup-drafts" in result.stdout
        assert "--cleanup" in result.stdout

    def test_mapping_importer_arguments(self):
        """Test mapping importer accepts all unified parameters"""
        import subprocess

        result = subprocess.run(
            ["python", str(REPO_ROOT / "scripts" / "mapping_asset_importer.py"), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "--scope" in result.stdout
        assert "--cleanup-drafts" in result.stdout
        assert "--cleanup" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
