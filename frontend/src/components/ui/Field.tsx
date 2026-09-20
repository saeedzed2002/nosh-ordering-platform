import { useId, type InputHTMLAttributes, type SelectHTMLAttributes } from "react";

type FieldSupportProps = {
  error?: string;
  hint?: string;
  id?: string;
  label: string;
};

type TextFieldProps = FieldSupportProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

type SelectOption = {
  label: string;
  value: string;
};

type SelectFieldProps = FieldSupportProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, "children" | "id"> & {
    options: SelectOption[];
  };

function getDescriptionIds(id: string, hint?: string, error?: string): string | undefined {
  const ids = [hint ? `${id}-hint` : undefined, error ? `${id}-error` : undefined].filter(
    Boolean,
  );

  return ids.length > 0 ? ids.join(" ") : undefined;
}

export function TextField({
  error,
  hint,
  id: providedId,
  label,
  ...inputProps
}: TextFieldProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const describedBy = getDescriptionIds(id, hint, error);

  return (
    <div className="nosh-field" data-invalid={Boolean(error) || undefined}>
      <label htmlFor={id}>{label}</label>
      <input
        {...inputProps}
        id={id}
        aria-describedby={describedBy}
        aria-invalid={Boolean(error) || undefined}
      />
      {hint ? <p id={`${id}-hint`}>{hint}</p> : null}
      {error ? <p id={`${id}-error`} role="alert">{error}</p> : null}
    </div>
  );
}

export function SelectField({
  error,
  hint,
  id: providedId,
  label,
  options,
  ...selectProps
}: SelectFieldProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const describedBy = getDescriptionIds(id, hint, error);

  return (
    <div className="nosh-field" data-invalid={Boolean(error) || undefined}>
      <label htmlFor={id}>{label}</label>
      <select
        {...selectProps}
        id={id}
        aria-describedby={describedBy}
        aria-invalid={Boolean(error) || undefined}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? <p id={`${id}-hint`}>{hint}</p> : null}
      {error ? <p id={`${id}-error`} role="alert">{error}</p> : null}
    </div>
  );
}
