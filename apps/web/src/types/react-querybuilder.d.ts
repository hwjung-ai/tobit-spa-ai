declare module "react-querybuilder" {
  import * as React from "react";

  export const QueryBuilder: React.ComponentType<Record<string, unknown>>;
  export function formatQuery(query: Record<string, unknown>, options?: Record<string, unknown>): string;
}
