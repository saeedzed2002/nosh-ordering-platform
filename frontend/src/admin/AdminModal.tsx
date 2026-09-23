import { type ReactNode, type RefObject } from "react";

import { X } from "lucide-react";
import { Dialog } from "radix-ui";

type AdminModalProps = {
  children: ReactNode;
  closeLabel: string;
  description: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  kicker: string;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
};

/**
 * A shared modal for consequential back-office actions. Radix provides the
 * dialog semantics, focus trap, escape handling, and focus restoration.
 */
export function AdminModal({
  children,
  closeLabel,
  description,
  initialFocusRef,
  kicker,
  onOpenChange,
  open,
  title,
}: AdminModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="admin-order-modal-backdrop" />
        <Dialog.Content
          className="admin-order-modal"
          onOpenAutoFocus={(event) => {
            if (initialFocusRef?.current) {
              event.preventDefault();
              initialFocusRef.current.focus();
            }
          }}
        >
          <Dialog.Close aria-label={closeLabel} className="admin-order-modal-close">
            <X aria-hidden="true" />
          </Dialog.Close>
          <p className="admin-kicker">{kicker}</p>
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
