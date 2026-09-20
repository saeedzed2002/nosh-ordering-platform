import { type ReactNode } from "react";

import { X } from "lucide-react";
import { Dialog } from "radix-ui";

import { IconButton } from "./Button";

type DrawerProps = {
  children: ReactNode;
  description: string;
  footer?: ReactNode;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
};

export function Drawer({
  children,
  description,
  footer,
  onOpenChange,
  open,
  title,
}: DrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="nosh-drawer-overlay" />
        <Dialog.Content className="nosh-drawer-content">
          <header className="nosh-drawer-header">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>{description}</Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <IconButton label={`Close ${title}`} variant="quiet">
                <X aria-hidden="true" />
              </IconButton>
            </Dialog.Close>
          </header>
          <div className="nosh-drawer-body">{children}</div>
          {footer ? <footer className="nosh-drawer-footer">{footer}</footer> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
