import type { Meta, StoryObj } from "@storybook/react-vite";

import { StatusBadge } from "./StatusBadge";

const meta = {
  title: "Primitives/Status badge",
  component: StatusBadge,
} satisfies Meta<typeof StatusBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const OperationalStates: Story = {
  args: {
    children: "Available",
    tone: "available",
  },
  render: () => (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
      <StatusBadge tone="available">Available</StatusBadge>
      <StatusBadge tone="preparing">Preparing</StatusBadge>
      <StatusBadge tone="ready">Ready</StatusBadge>
      <StatusBadge tone="unavailable">Unavailable</StatusBadge>
    </div>
  ),
};
