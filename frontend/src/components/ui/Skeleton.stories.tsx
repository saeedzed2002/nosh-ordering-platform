import type { Meta, StoryObj } from "@storybook/react-vite";

import { Skeleton } from "./Skeleton";

const meta = {
  title: "Feedback/Skeleton",
  component: Skeleton,
} satisfies Meta<typeof Skeleton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ContentPlaceholder: Story = {
  args: {},
  render: () => (
    <div style={{ display: "grid", gap: "0.75rem", maxWidth: "24rem" }}>
      <Skeleton className="nosh-skeleton-line nosh-skeleton-line--title" />
      <Skeleton className="nosh-skeleton-line" />
      <Skeleton className="nosh-skeleton-line nosh-skeleton-line--short" />
    </div>
  ),
};
