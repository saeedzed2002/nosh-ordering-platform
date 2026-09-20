import type { Meta, StoryObj } from "@storybook/react-vite";

import heroImage from "../../assets/nosh-hero-food.webp";

import { FoodCard } from "./FoodCard";

const meta = {
  title: "Menu/Food card",
  component: FoodCard,
  args: {
    alt: "Grilled chicken with hummus, chickpeas, cucumber, herbs, and flatbread",
    description: "Grilled chicken, hummus, chickpeas, cucumber, herbs, and flatbread.",
    image: heroImage,
    name: "Harissa chicken",
    price: "$14.50",
    status: "available",
    tags: ["Gluten-aware", "Spicy"],
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: "27rem" }}>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof FoodCard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Available: Story = {};

export const Unavailable: Story = {
  args: {
    status: "unavailable",
  },
};
