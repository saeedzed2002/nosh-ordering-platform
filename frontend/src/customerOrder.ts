import type { CustomerMenuItem } from "./customerCatalog";

export type CustomerSelections = Record<string, string[]>;

export function selectedOptionIds(selections: CustomerSelections): string[] {
  return Object.values(selections).flat();
}

export function selectionIssues(
  item: CustomerMenuItem,
  selections: CustomerSelections,
): Record<string, string> {
  const issues: Record<string, string> = {};
  for (const group of item.option_groups) {
    const selected = selections[group.id] ?? [];
    if (selected.length < group.minimum_selections) {
      issues[group.id] = group.minimum_selections === 1
        ? `Choose one option for ${group.name}.`
        : `Choose at least ${group.minimum_selections} options for ${group.name}.`;
    } else if (selected.length > group.maximum_selections) {
      issues[group.id] = `Choose no more than ${group.maximum_selections} options for ${group.name}.`;
    }
  }
  return issues;
}

export function previewCustomerPrice(
  item: CustomerMenuItem,
  selections: CustomerSelections,
): number {
  const selected = new Set(selectedOptionIds(selections));
  return item.final_price_minor + item.option_groups.flatMap((group) => group.options)
    .filter((option) => selected.has(option.id))
    .reduce((total, option) => total + option.price_delta_minor, 0);
}

export function customerCartLineId(): string {
  return globalThis.crypto?.randomUUID?.().replaceAll("-", "") ?? `line${Date.now()}`;
}
