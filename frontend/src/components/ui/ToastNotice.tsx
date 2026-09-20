import { X } from "lucide-react";
import { Toast } from "radix-ui";

import { IconButton } from "./Button";

export type ToastMessage = {
  description: string;
  title: string;
};

type ToastNoticeProps = {
  notice: ToastMessage | null;
  onOpenChange: (open: boolean) => void;
};

export function ToastNotice({ notice, onOpenChange }: ToastNoticeProps) {
  return (
    <Toast.Root className="nosh-toast" open={notice !== null} onOpenChange={onOpenChange}>
      <div>
        <Toast.Title>{notice?.title}</Toast.Title>
        <Toast.Description>{notice?.description}</Toast.Description>
      </div>
      <Toast.Close asChild>
        <IconButton label="Dismiss message" variant="quiet">
          <X aria-hidden="true" />
        </IconButton>
      </Toast.Close>
    </Toast.Root>
  );
}

export function ToastViewport() {
  return <Toast.Viewport className="nosh-toast-viewport" />;
}
