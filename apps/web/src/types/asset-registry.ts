import { SourceAssetResponse, SchemaAssetResponse, ResolverAssetResponse, ConnectionTestResult } from "../../types";

export type {
  SourceAsset,
  SourceAssetCreate,
  SourceAssetUpdate,
  SourceAssetResponse,
  SourceListResponse,
  ConnectionTestResult,
  SchemaAsset,
  SchemaAssetCreate,
  SchemaAssetUpdate,
  SchemaAssetResponse,
  SchemaListResponse,
  ResolverAsset,
  ResolverAssetCreate,
  ResolverAssetUpdate,
  ResolverAssetResponse,
  ResolverListResponse,
  ResolverConfig,
  ResolverRule,
  AliasMapping,
  PatternRule,
  TransformationRule,
  ResolverSimulationRequest,
  ResolverSimulationResult,
} from "../../types";

// Re-export from types for convenience
export { SourceAssetResponse, SchemaAssetResponse, ResolverAssetResponse, ConnectionTestResult };

// Type guards
export const isSourceAsset = (asset: unknown): asset is SourceAssetResponse => {
  return asset !== null && typeof asset === 'object' && 'asset_type' in asset && asset.asset_type === "source";
};

export const isSchemaAsset = (asset: unknown): asset is SchemaAssetResponse => {
  return asset !== null && typeof asset === 'object' && 'asset_type' in asset && asset.asset_type === "schema";
};

export const isResolverAsset = (asset: unknown): asset is ResolverAssetResponse => {
  return asset !== null && typeof asset === 'object' && 'asset_type' in asset && asset.asset_type === "resolver";
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