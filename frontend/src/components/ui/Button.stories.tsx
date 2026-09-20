import type { Meta, StoryObj } from "@storybook/react-vite";

import { ShoppingBag } from "lucide-react";

import { Button, IconButton } from "./Button";

const meta = {
  title: "Primitives/Button",
  component: Button,
  args: {
    children: "Order now",
  },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Primary: Story = {};

export const Secondary: Story = {
  args: {
    children: "Add to cart",
    variant: "secondary",
  },
};

export const Disabled: Story = {
  args: {
    children: "Unavailable",
    disabled: true,
  },
};

export const Loading: Story = {
  args: {
    children: "Adding to cart",
    loading: true,
  },
};

export const OnInverseSurface: Story = {
  args: {
    children: "Continue exploring",
    variant: "secondary",
  },
  decorators: [
    (Story) => (
      <div className="nosh-inverse-surface">
        <Story />
      </div>
    ),
  ],
};

export const IconOnly: Story = {
  render: () => (
    <IconButton label="Open cart" variant="secondary">
      <ShoppingBag aria-hidden="true" />
    </IconButton>
  ),
};
