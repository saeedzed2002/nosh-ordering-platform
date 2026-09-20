import { useState } from "react";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "./Button";
import { Drawer } from "./Drawer";

function DrawerExample() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Open cart drawer</Button>
      <Drawer
        description="A focus-managed component for short, related tasks."
        open={open}
        title="Your cart"
        onOpenChange={setOpen}
        footer={<Button variant="secondary" onClick={() => setOpen(false)}>Continue exploring</Button>}
      >
        <p>Cart contents are introduced with the validated ordering flow.</p>
      </Drawer>
    </>
  );
}

const meta = {
  title: "Overlays/Drawer",
  component: Drawer,
} satisfies Meta<typeof Drawer>;

export default meta;

type Story = StoryObj<typeof meta>;

export const FocusManaged: Story = {
  args: {
    children: null,
    description: "A focus-managed component for short, related tasks.",
    open: false,
    title: "Your cart",
    onOpenChange: () => undefined,
  },
  render: () => <DrawerExample />,
};
