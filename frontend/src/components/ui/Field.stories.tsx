import type { Meta, StoryObj } from "@storybook/react-vite";

import { SelectField, TextField } from "./Field";

const meta = {
  title: "Primitives/Fields",
  component: TextField,
} satisfies Meta<typeof TextField>;

export default meta;

type Story = StoryObj<typeof meta>;

export const TextStates: Story = {
  args: {
    label: "Delivery address",
  },
  render: () => (
    <div style={{ display: "grid", gap: "1.5rem", maxWidth: "26rem" }}>
      <TextField label="Delivery address" placeholder="12 Market Street" />
      <TextField
        error="Enter a delivery address before continuing."
        label="Delivery address"
        value=""
        readOnly
      />
      <SelectField
        label="Fulfilment"
        options={[
          { value: "pickup", label: "Pickup" },
          { value: "delivery", label: "Delivery" },
        ]}
      />
    </div>
  ),
};
