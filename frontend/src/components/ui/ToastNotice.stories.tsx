import { useState } from "react";

import type { Meta, StoryObj } from "@storybook/react-vite";

import { Toast } from "radix-ui";

import { Button } from "./Button";
import { ToastNotice, ToastViewport, type ToastMessage } from "./ToastNotice";

function ToastExample() {
  const [notice, setNotice] = useState<ToastMessage | null>({
    title: "Fulfilment updated",
    description: "Pickup is selected. Your choice will be retained in the cart.",
  });

  return (
    <Toast.Provider>
      <Button onClick={() => setNotice({
        title: "Fulfilment updated",
        description: "Delivery is selected. The address step arrives with checkout.",
      })}>
        Show notification
      </Button>
      <ToastNotice notice={notice} onOpenChange={(open) => !open && setNotice(null)} />
      <ToastViewport />
    </Toast.Provider>
  );
}

const meta = {
  title: "Feedback/Toast",
  component: ToastNotice,
  args: {
    notice: null,
    onOpenChange: () => undefined,
  },
} satisfies Meta<typeof ToastNotice>;

export default meta;

type Story = StoryObj<typeof meta>;

export const DismissibleNotice: Story = {
  render: () => <ToastExample />,
};
