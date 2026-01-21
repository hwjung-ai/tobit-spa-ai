import { ScreenSchemaV1, Component } from "./screen.schema";
import { getComponentDescriptor } from "./component-registry";

/**
 * Generate a unique component ID based on type
 */
export function generateComponentId(type: string, existingComponents: Component[]): string {
  let counter = 1;
  let id = `${type}_${counter}`;
  while (existingComponents.some(c => c.id === id)) {
    counter++;
    id = `${type}_${counter}`;
  }
  return id;
}

/**
 * Create a default component with minimal props
 */
export function createDefaultComponent(type: string, id: string): Component {
  const descriptor = getComponentDescriptor(type);
  return {
    id,
    type,
    label: descriptor?.label || type,
    props: {},
  };
}

/**
 * Add a component to schema at specified index or at end
 */
export function addComponentToSchema(
  schema: ScreenSchemaV1,
  component: Component,
  index?: number
): ScreenSchemaV1 {
  const newComponents = [...schema.components];
  if (index !== undefined && index >= 0 && index <= newComponents.length) {
    newComponents.splice(index, 0, component);
  } else {
    newComponents.push(component);
  }
  return { ...schema, components: newComponents };
}

/**
 * Delete component from schema
 */
export function deleteComponentFromSchema(
  schema: ScreenSchemaV1,
  componentId: string
): ScreenSchemaV1 {
  const newComponents = schema.components.filter(c => c.id !== componentId);
  return { ...schema, components: newComponents };
}

/**
 * Move component up or down in schema
 */
export function moveComponentInSchema(
  schema: ScreenSchemaV1,
  componentId: string,
  direction: "up" | "down"
): ScreenSchemaV1 {
  const idx = schema.components.findIndex(c => c.id === componentId);
  if (idx === -1) return schema;

  const newIndex = direction === "up" ? idx - 1 : idx + 1;
  if (newIndex < 0 || newIndex >= schema.components.length) return schema;

  const newComponents = [...schema.components];
  [newComponents[idx], newComponents[newIndex]] = [newComponents[newIndex], newComponents[idx]];

  return { ...schema, components: newComponents };
}

/**
 * Find component by ID
 */
export function findComponentById(
  schema: ScreenSchemaV1,
  componentId: string
): Component | undefined {
  return schema.components.find(c => c.id === componentId);
}

/**
 * Update component props in schema
 */
export function updateComponentPropsInSchema(
  schema: ScreenSchemaV1,
  componentId: string,
  props: Record<string, unknown>
): ScreenSchemaV1 {
  const newComponents = schema.components.map(c =>
    c.id === componentId
      ? { ...c, props: { ...c.props, ...props } }
      : c
  );
  return { ...schema, components: newComponents };
}

/**
 * Update component label in schema
 */
export function updateComponentLabelInSchema(
  schema: ScreenSchemaV1,
  componentId: string,
  label: string
): ScreenSchemaV1 {
  const newComponents = schema.components.map(c =>
    c.id === componentId
      ? { ...c, label }
      : c
  );
  return { ...schema, components: newComponents };
}

/**
 * Update component bind path in schema
 */
export function updateComponentBindInSchema(
  schema: ScreenSchemaV1,
  componentId: string,
  bind: string
): ScreenSchemaV1 {
  const newComponents = schema.components.map(c =>
    c.id === componentId
      ? { ...c, bind }
      : c
  );
  return { ...schema, components: newComponents };
}

/**
 * Duplicate component in schema
 */
export function duplicateComponentInSchema(
  schema: ScreenSchemaV1,
  componentId: string
): ScreenSchemaV1 {
  const component = findComponentById(schema, componentId);
  if (!component) return schema;

  const newId = generateComponentId(component.type, schema.components);
  const newComponent: Component = {
    ...JSON.parse(JSON.stringify(component)),
    id: newId,
  };

  return addComponentToSchema(schema, newComponent, schema.components.indexOf(component) + 1);
}

/**
 * Get component at index
 */
export function getComponentAtIndex(
  schema: ScreenSchemaV1,
  index: number
): Component | undefined {
  return schema.components[index];
}

/**
 * Find index of component by ID
 */
export function findComponentIndex(
  schema: ScreenSchemaV1,
  componentId: string
): number {
  return schema.components.findIndex(c => c.id === componentId);
}

/**
 * Validate component structure
 */
export function isValidComponent(component: unknown): boolean {
  return (
    component &&
    typeof component === "object" &&
    typeof component.id === "string" &&
    typeof component.type === "string" &&
    ["text", "markdown", "button", "input", "table", "chart", "badge", "tabs", "modal", "keyvalue", "divider"].includes(component.type)
  );
}

/**
 * Validate schema structure
 */
export function isValidSchema(schema: unknown): boolean {
  return (
    schema &&
    typeof schema === "object" &&
    typeof schema.screen_id === "string" &&
    schema.layout &&
    typeof schema.layout === "object" &&
    Array.isArray(schema.components) &&
    schema.components.every((c: unknown) => isValidComponent(c)) &&
    schema.state &&
    typeof schema.state === "object" &&
    typeof schema.bindings === "object"
  );
}
