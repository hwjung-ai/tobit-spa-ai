-- Migration script for API Manager ↔ Tools Integration
-- Run this script directly in PostgreSQL to apply migrations 0050 and 0051

-- =====================================================
-- 0050: Add tools linkage to api_definitions table
-- =====================================================

ALTER TABLE api_definitions 
ADD COLUMN IF NOT EXISTS linked_to_tool_id UUID;

ALTER TABLE api_definitions 
ADD COLUMN IF NOT EXISTS linked_to_tool_name TEXT;

ALTER TABLE api_definitions 
ADD COLUMN IF NOT EXISTS linked_at TIMESTAMP;

-- Note: No FK constraint - managed at application level to avoid bidirectional FK issues
-- when unlinking. Linkage is enforced by business logic.

-- =====================================================
-- 0051: Add API Manager linkage to tb_asset_registry table
-- =====================================================

ALTER TABLE tb_asset_registry 
ADD COLUMN IF NOT EXISTS linked_from_api_id UUID;

ALTER TABLE tb_asset_registry 
ADD COLUMN IF NOT EXISTS linked_from_api_name TEXT;

ALTER TABLE tb_asset_registry 
ADD COLUMN IF NOT EXISTS linked_from_api_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE tb_asset_registry 
ADD COLUMN IF NOT EXISTS import_mode TEXT;

ALTER TABLE tb_asset_registry 
ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP WITH TIME ZONE;

-- Note: No FK constraint - managed at application level to avoid bidirectional FK issues
-- when unlinking. Linkage is enforced by business logic.

-- =====================================================
-- Update alembic_version table
-- =====================================================

UPDATE alembic_version 
SET version_num = '0051' 
WHERE version_num = '0049_add_api_definitions_runtime_policy';

-- =====================================================
-- Verification queries (run these to verify success)
-- =====================================================

-- Check api_definitions columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'api_definitions' 
AND column_name IN ('linked_to_tool_id', 'linked_to_tool_name', 'linked_at')
ORDER BY ordinal_position;

-- Check tb_asset_registry columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'tb_asset_registry' 
AND column_name IN ('linked_from_api_id', 'linked_from_api_name', 'linked_from_api_at', 'import_mode', 'last_synced_at')
ORDER BY ordinal_position;

-- Check alembic_version
SELECT * FROM alembic_version;

-- Note: No foreign key constraints - linkage is managed at application level
