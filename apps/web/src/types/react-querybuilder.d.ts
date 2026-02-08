declare module "react-querybuilder" {
  import * as React from "react";

  export const QueryBuilder: React.ComponentType<any>;
  export function formatQuery(query: any, options?: any): string;
}
