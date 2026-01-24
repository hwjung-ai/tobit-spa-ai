// Frontend type definitions for asset registry endpoints

export type SourceType =
  | "postgresql"
  | "mysql"
  | "redis"
  | "mongodb"
  | "kafka"
  | "s3"
  | "bigquery"
  | "snowflake";

export interface SourceConnection {
  host: string;
  port: number;
  username: string;
  database?: string | null;
  password_encrypted?: string | null;
  secret_key_ref?: string | null;
  timeout?: number;
  max_connections?: number | null;
  ssl_mode?: string | null;
  connection_params?: Record<string, unknown> | null;
  description?: string | null;
  test_query?: string | null;
}

export interface SourceAsset {
  asset_type: "source";
  name: string;
  description?: string | null;
  version: number;
  status: string;
  source_type: SourceType;
  connection: SourceConnection;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
  created_by?: string | null;
  published_by?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  spec_json?: Record<string, unknown> | null;
}

export interface SourceAssetCreate {
  name: string;
  description?: string | null;
  source_type: SourceType;
  connection: SourceConnection;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface SourceAssetUpdate {
  name?: string | null;
  description?: string | null;
  source_type?: SourceType;
  connection?: SourceConnection;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface SourceAssetResponse extends SourceAsset {
  asset_id: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  error_details?: string | null;
  execution_time_ms?: number | null;
  test_result?: Record<string, unknown> | null;
}

export interface SourceListResponse {
  assets: SourceAssetResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface SchemaColumn {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  foreign_key_table?: string | null;
  foreign_key_column?: string | null;
  default_value?: string | null;
  description?: string | null;
  constraints?: Record<string, unknown> | null;
}

export interface SchemaTable {
  name: string;
  schema_name: string;
  description?: string | null;
  columns: SchemaColumn[];
  indexes?: Record<string, unknown> | null;
  constraints?: Record<string, unknown> | null;
  tags?: Record<string, unknown> | null;
}

export interface SchemaCatalog {
  name: string;
  description?: string | null;
  source_ref: string;
  tables: SchemaTable[];
  last_scanned_at?: string | null;
  scan_status: "pending" | "scanning" | "completed" | "failed";
  scan_metadata?: Record<string, unknown> | null;
  table_count?: number;
  column_count?: number;
}

export interface SchemaAsset {
  asset_type: "schema";
  name: string;
  description?: string | null;
  version: number;
  status: string;
  catalog: SchemaCatalog;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
  created_by?: string | null;
  published_by?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  spec_json?: Record<string, unknown> | null;
}

export interface SchemaAssetCreate {
  name: string;
  description?: string | null;
  source_ref: string;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface SchemaAssetUpdate {
  name?: string | null;
  description?: string | null;
  catalog?: SchemaCatalog | null;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface SchemaAssetResponse extends SchemaAsset {
  asset_id: string;
}

export interface SchemaListResponse {
  assets: SchemaAssetResponse[];
  total: number;
  page: number;
  page_size: number;
}

export type ResolverType = "alias_mapping" | "pattern_rule" | "transformation";

export interface AliasMapping {
  source_entity: string;
  target_entity: string;
  namespace?: string | null;
  description?: string | null;
  is_active?: boolean;
  priority?: number;
  extra_metadata?: Record<string, unknown> | null;
}

export interface PatternRule {
  name: string;
  pattern: string;
  replacement: string;
  description?: string | null;
  is_active?: boolean;
  priority?: number;
  extra_metadata?: Record<string, unknown> | null;
}

export interface TransformationRule {
  name: string;
  transformation_type: string;
  field_name: string;
  description?: string | null;
  is_active?: boolean;
  priority?: number;
  parameters?: Record<string, unknown> | null;
  extra_metadata?: Record<string, unknown> | null;
}

export interface ResolverRule {
  rule_type: ResolverType;
  name: string;
  description?: string | null;
  is_active?: boolean;
  priority?: number;
  extra_metadata?: Record<string, unknown> | null;
  rule_data: AliasMapping | PatternRule | TransformationRule;
}

export interface ResolverConfig {
  name: string;
  description?: string | null;
  rules: ResolverRule[];
  default_namespace?: string | null;
  tags?: Record<string, unknown> | null;
  version?: number;
}

export interface ResolverAsset {
  asset_type: "resolver";
  name: string;
  description?: string | null;
  version: number;
  status: string;
  config: ResolverConfig;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
  created_by?: string | null;
  published_by?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  spec_json?: Record<string, unknown> | null;
}

export interface ResolverAssetCreate {
  name: string;
  description?: string | null;
  config: ResolverConfig;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface ResolverAssetUpdate {
  name?: string | null;
  description?: string | null;
  config?: ResolverConfig | null;
  scope?: string | null;
  tags?: Record<string, unknown> | null;
}

export interface ResolverAssetResponse extends ResolverAsset {
  asset_id: string;
}

export interface ResolverListResponse {
  assets: ResolverAssetResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ResolverSimulationRequest {
  config: ResolverConfig;
  test_entities: string[];
  simulation_options?: Record<string, unknown> | null;
}

export interface ResolverSimulationResult {
  original_entity: string;
  resolved_entity: string;
  transformations_applied: string[];
  confidence_score: number;
  matched_rules: string[];
  extra_metadata?: Record<string, unknown> | null;
}

// Type guards
export const isSourceAsset = (asset: unknown): asset is SourceAssetResponse => {
  return asset !== null && typeof asset === "object" && "asset_type" in asset && asset.asset_type === "source";
};

export const isSchemaAsset = (asset: unknown): asset is SchemaAssetResponse => {
  return asset !== null && typeof asset === "object" && "asset_type" in asset && asset.asset_type === "schema";
};

export const isResolverAsset = (asset: unknown): asset is ResolverAssetResponse => {
  return asset !== null && typeof asset === "object" && "asset_type" in asset && asset.asset_type === "resolver";
};

// Utility types
export type AssetType = "source" | "schema" | "resolver";

export type AssetResponse =
  | SourceAssetResponse
  | SchemaAssetResponse
  | ResolverAssetResponse;

export type AssetListResponse =
  | SourceListResponse
  | SchemaListResponse
  | ResolverListResponse;
