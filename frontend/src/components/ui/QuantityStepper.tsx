import { Minus, Plus } from "lucide-react";

import { IconButton } from "./Button";

type QuantityStepperProps = {
  disabled?: boolean;
  max?: number;
  min?: number;
  onValueChange: (value: number) => void;
  value: number;
};

export function QuantityStepper({
  disabled = false,
  max,
  min = 1,
  onValueChange,
  value,
}: QuantityStepperProps) {
  const decrementDisabled = disabled || value <= min;
  const incrementDisabled = disabled || (max !== undefined && value >= max);

  return (
    <div className="nosh-quantity-stepper" aria-label="Quantity selector">
      <IconButton
        disabled={decrementDisabled}
        label="Decrease quantity"
        variant="secondary"
        onClick={() => onValueChange(value - 1)}
      >
        <Minus aria-hidden="true" />
      </IconButton>
      <output aria-live="polite">{value}</output>
      <IconButton
        disabled={incrementDisabled}
        label="Increase quantity"
        variant="secondary"
        onClick={() => onValueChange(value + 1)}
      >
        <Plus aria-hidden="true" />
      </IconButton>
    </div>
  );
}
