import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { LoaderCircle } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "danger" | "quiet";
type ButtonSize = "default" | "compact" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  loading?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

function classNames(...values: Array<string | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    children,
    className,
    disabled,
    loading = false,
    size = "default",
    type = "button",
    variant = "primary",
    ...props
  },
  ref,
) {
  return (
    <button
      {...props}
      ref={ref}
      className={classNames("nosh-button", className)}
      data-size={size}
      data-variant={variant}
      disabled={disabled || loading}
      type={type}
      aria-busy={loading || undefined}
    >
      {loading ? <LoaderCircle aria-hidden="true" className="nosh-button-spinner" /> : null}
      {children}
    </button>
  );
});

type IconButtonProps = Omit<ButtonProps, "children" | "size"> & {
  label: string;
  children: ReactNode;
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ children, className, label, ...props }, ref) {
    return (
      <Button
        {...props}
        ref={ref}
        aria-label={label}
        className={classNames("nosh-icon-button", className)}
        size="icon"
      >
        {children}
      </Button>
    );
  },
);
