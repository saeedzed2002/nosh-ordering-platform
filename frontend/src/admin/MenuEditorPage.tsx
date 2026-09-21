import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  CircleAlert,
  Eye,
  FileText,
  ImagePlus,
  LoaderCircle,
  PackagePlus,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/Field";
import { ApiError } from "./api";
import {
  type AvailabilityState,
  type MenuItem,
  type MenuOption,
  type MenuOptionGroup,
  type MenuSetup,
  type MenuWritePayload,
  type OptionKind,
  type PublicationState,
  currencyInputToMinor,
  formatPrice,
  fromLocalInputValue,
  minorToCurrencyInput,
  slugFromName,
  splitTerms,
  toLocalInputValue,
} from "./menuTypes";
import { ProtectedMediaImage } from "./ProtectedMediaImage";
import { useAdminSession } from "./session";

type EditorForm = {
  name: string;
  slug: string;
  description: string;
  category_id: string;
  media_id: string;
  ingredients_text: string;
  dietary_tags_text: string;
  base_price_minor: number;
  demo_discount_minor: number;
  display_order: number;
  publication_state: PublicationState;
  allergen_ids: string[];
  option_groups: MenuOptionGroup[];
  location_id: string;
  availability_state: AvailabilityState;
  available_from: string;
  available_until: string;
};

const stepLabels = ["Plate basics", "Price & service", "Choices & care", "Review"];

function emptyOption(): MenuOption {
  return { name: "", price_delta_minor: 0, is_available: true };
}

function newOptionGroup(): MenuOptionGroup {
  return {
    name: "",
    kind: "choice",
    minimum_selections: 0,
    maximum_selections: 1,
    options: [emptyOption()],
  };
}

function emptyForm(setup: MenuSetup): EditorForm {
  return {
    name: "",
    slug: "",
    description: "",
    category_id: setup.categories[0]?.id ?? "",
    media_id: setup.media.find((media) => media.publication_state === "published")?.id ?? "",
    ingredients_text: "",
    dietary_tags_text: "",
    base_price_minor: 0,
    demo_discount_minor: 0,
    display_order: 0,
    publication_state: "draft",
    allergen_ids: [],
    option_groups: [],
    location_id: setup.locations[0]?.id ?? "",
    availability_state: "available",
    available_from: "",
    available_until: "",
  };
}

function formFromItem(item: MenuItem): EditorForm {
  return {
    name: item.name,
    slug: item.slug,
    description: item.description,
    category_id: item.category.id,
    media_id: item.media.id,
    ingredients_text: item.ingredients.join(", "),
    dietary_tags_text: item.dietary_tags.join(", "),
    base_price_minor: item.base_price_minor,
    demo_discount_minor: item.demo_discount_minor,
    display_order: item.display_order,
    publication_state: item.publication_state,
    allergen_ids: item.allergens.map((allergen) => allergen.id),
    option_groups: item.option_groups.map((group) => ({
      ...group,
      options: group.options.map((option) => ({ ...option })),
    })),
    location_id: item.availability.location_id,
    availability_state: item.availability.state,
    available_from: toLocalInputValue(item.availability.available_from),
    available_until: toLocalInputValue(item.availability.available_until),
  };
}

function formToPayload(form: EditorForm): MenuWritePayload {
  const availability = {
    location_id: form.location_id,
    state: form.availability_state,
    ...(form.availability_state === "scheduled"
      ? {
          available_from: fromLocalInputValue(form.available_from),
          available_until: fromLocalInputValue(form.available_until),
        }
      : {}),
  };
  return {
    name: form.name.trim(),
    slug: form.slug,
    description: form.description.trim(),
    category_id: form.category_id,
    media_id: form.media_id,
    ingredients: splitTerms(form.ingredients_text),
    dietary_tags: splitTerms(form.dietary_tags_text),
    base_price_minor: form.base_price_minor,
    demo_discount_minor: form.demo_discount_minor,
    display_order: form.display_order,
    publication_state: form.publication_state,
    allergen_ids: form.allergen_ids,
    option_groups: form.option_groups.map((group) => ({
      name: group.name.trim(),
      kind: group.kind,
      minimum_selections: group.minimum_selections,
      maximum_selections: group.maximum_selections,
      options: group.options.map((option) => ({
        name: option.name.trim(),
        price_delta_minor: option.price_delta_minor,
        is_available: option.is_available,
      })),
    })),
    availability,
  };
}

function validationForStep(form: EditorForm, setup: MenuSetup, step: number): string | null {
  if (step === 0) {
    if (!form.name.trim() || !form.description.trim()) {
      return "Give the dish a name and a useful customer-facing description.";
    }
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(form.slug)) {
      return "The URL name needs lowercase letters, numbers, and single dashes.";
    }
    if (!form.category_id || !form.media_id) {
      return "Choose both a category and an image before continuing.";
    }
  }
  if (step === 1) {
    if (!Number.isFinite(form.base_price_minor) || form.base_price_minor < 0) {
      return "Give the dish a valid non-negative base price.";
    }
    if (form.demo_discount_minor < 0 || form.demo_discount_minor > form.base_price_minor) {
      return "The demo discount must be between zero and the base price.";
    }
    if (!form.location_id) {
      return "Choose the local service location.";
    }
    if (form.availability_state === "scheduled") {
      if (!form.available_from || !form.available_until) {
        return "A schedule needs both a start and an end time.";
      }
      if (new Date(form.available_until) <= new Date(form.available_from)) {
        return "The schedule end must be after the start.";
      }
    }
    const selectedMedia = setup.media.find((media) => media.id === form.media_id);
    const selectedCategory = setup.categories.find((category) => category.id === form.category_id);
    if (
      form.publication_state === "published" &&
      (selectedMedia?.publication_state !== "published" || !selectedCategory?.is_published)
    ) {
      return "A customer-live dish needs a customer-live image and category.";
    }
  }
  if (step === 2) {
    for (const group of form.option_groups) {
      if (!group.name.trim()) {
        return "Give every choice group a clear customer-facing name.";
      }
      if (group.options.length === 0 || group.options.some((option) => !option.name.trim())) {
        return "Every choice group needs at least one named option.";
      }
      if (
        group.options.some(
          (option) => !Number.isFinite(option.price_delta_minor) || option.price_delta_minor < 0,
        )
      ) {
        return "Give every extra price a valid non-negative amount.";
      }
      const activeCount = group.options.filter((option) => option.is_available).length;
      if (
        group.maximum_selections < group.minimum_selections ||
        group.maximum_selections > group.options.length ||
        group.minimum_selections > activeCount
      ) {
        return "Check the required and maximum choices for each option group.";
      }
    }
  }
  return null;
}

function displayTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
  }).format(new Date(value));
}

export function MenuEditorPage() {
  const { request } = useAdminSession();
  const { slug } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(slug);
  const [setup, setSetup] = useState<MenuSetup | null>(null);
  const [form, setForm] = useState<EditorForm | null>(null);
  const [item, setItem] = useState<MenuItem | null>(null);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const itemRequest = slug
      ? request<MenuItem>(`/api/v1/admin/menu/${slug}`)
      : Promise.resolve(null);
    void Promise.all([request<MenuSetup>("/api/v1/admin/menu/setup"), itemRequest])
      .then(([nextSetup, nextItem]) => {
        if (!active) {
          return;
        }
        setSetup(nextSetup);
        setItem(nextItem);
        setForm(nextItem ? formFromItem(nextItem) : emptyForm(nextSetup));
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof ApiError ? reason.message : "The menu item could not be opened.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [request, slug]);

  const selectedMedia = useMemo(
    () => setup?.media.find((media) => media.id === form?.media_id) ?? null,
    [form?.media_id, setup?.media],
  );
  const selectedCategory = useMemo(
    () => setup?.categories.find((category) => category.id === form?.category_id) ?? null,
    [form?.category_id, setup?.categories],
  );

  function updateForm(changes: Partial<EditorForm>) {
    setForm((current) => (current ? { ...current, ...changes } : current));
  }

  function moveTo(nextStep: number) {
    if (!form || !setup) {
      return;
    }
    const problem = validationForStep(form, setup, step);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    setStep(nextStep);
  }

  function updateGroup(index: number, changes: Partial<MenuOptionGroup>) {
    updateForm({
      option_groups: form?.option_groups.map((group, groupIndex) =>
        groupIndex === index ? { ...group, ...changes } : group,
      ) ?? [],
    });
  }

  function updateOption(groupIndex: number, optionIndex: number, changes: Partial<MenuOption>) {
    if (!form) {
      return;
    }
    updateGroup(groupIndex, {
      options: form.option_groups[groupIndex].options.map((option, currentIndex) =>
        currentIndex === optionIndex ? { ...option, ...changes } : option,
      ),
    });
  }

  function toggleAllergen(allergenId: string) {
    if (!form) {
      return;
    }
    updateForm({
      allergen_ids: form.allergen_ids.includes(allergenId)
        ? form.allergen_ids.filter((id) => id !== allergenId)
        : [...form.allergen_ids, allergenId],
    });
  }

  async function saveItem() {
    if (!form || !setup) {
      return;
    }
    for (let currentStep = 0; currentStep < stepLabels.length - 1; currentStep += 1) {
      const problem = validationForStep(form, setup, currentStep);
      if (problem) {
        setStep(currentStep);
        setError(problem);
        return;
      }
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await request<MenuItem>(
        isEditing ? `/api/v1/admin/menu/${slug}` : "/api/v1/admin/menu",
        {
          method: isEditing ? "PUT" : "POST",
          body: JSON.stringify(formToPayload(form)),
        },
      );
      setItem(saved);
      setForm(formFromItem(saved));
      setNotice(
        saved.publication_state === "published"
          ? "Saved. This dish is now available through the public catalog API."
          : "Saved as a private draft.",
      );
      if (!isEditing) {
        navigate(`/admin/menu/${saved.slug}`, { replace: true });
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The dish could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="admin-inline-loading"><LoaderCircle aria-hidden="true" /> Opening the plate editor…</div>;
  }

  if (!setup || !form) {
    return <div className="admin-empty-state">The plate editor is unavailable.</div>;
  }

  return (
    <div className="admin-menu-editor">
      <header className="admin-menu-editor-heading">
        <div>
          <Link className="admin-editor-back-link" to="/admin/menu"><ChevronLeft aria-hidden="true" /> Back to menu</Link>
          <p className="admin-kicker">{isEditing ? "Edit dish" : "New dish"}</p>
          <h1>{isEditing ? `Refine ${item?.name ?? "this dish"}.` : "Build one plate at a time."}</h1>
          <p>Each step checks the customer-facing detail before you save it.</p>
        </div>
        <div className={`admin-state-chip ${form.publication_state}`}>{form.publication_state === "published" ? "Customer live" : "Private draft"}</div>
      </header>

      {error ? <p className="admin-form-error" role="alert"><CircleAlert aria-hidden="true" /> {error}</p> : null}
      {notice ? <p className="admin-form-notice" role="status"><CheckCircle2 aria-hidden="true" /> {notice}</p> : null}

      <ol className="admin-menu-steps" aria-label="Dish editor steps">
        {stepLabels.map((label, index) => (
          <li key={label} className={index === step ? "active" : index < step ? "complete" : undefined}>
            <button type="button" onClick={() => (index <= step ? setStep(index) : moveTo(index))}>
              <span>{String(index + 1).padStart(2, "0")}</span>{label}
            </button>
          </li>
        ))}
      </ol>

      <div className="admin-menu-editor-layout">
        <section className="admin-menu-editor-panel" aria-labelledby="menu-step-title">
          {step === 0 ? (
            <div className="admin-menu-step">
              <div className="admin-panel-heading">
                <div><p className="admin-kicker">Step 01</p><h2 id="menu-step-title">Name the plate and choose its image.</h2></div>
                <PackagePlus aria-hidden="true" />
              </div>
              <TextField label="Dish name" maxLength={160} value={form.name} onChange={(event) => updateForm({ name: event.target.value, slug: form.slug || slugFromName(event.target.value) })} />
              <TextField label="URL name" hint="Used for the public dish link later in the project." maxLength={160} value={form.slug} onChange={(event) => updateForm({ slug: slugFromName(event.target.value) })} />
              <label className="admin-textarea-field" htmlFor="menu-description">Customer-facing description<textarea id="menu-description" rows={5} value={form.description} onChange={(event) => updateForm({ description: event.target.value })} /></label>
              <label className="admin-select-field">Category<select value={form.category_id} onChange={(event) => updateForm({ category_id: event.target.value })}>{setup.categories.map((category) => <option key={category.id} value={category.id}>{category.name}{category.is_published ? "" : " — hidden"}</option>)}</select></label>
              <div className="admin-menu-image-picker">
                <div><label>Dish image</label><p>Choose an image that is already described in the media library.</p></div>
                <div className="admin-menu-image-grid">
                  {setup.media.map((media) => (
                    <button key={media.id} className={form.media_id === media.id ? "selected" : undefined} type="button" onClick={() => updateForm({ media_id: media.id })}>
                      <ProtectedMediaImage alt={media.alt_text} mediaId={media.id} />
                      <span>{media.original_filename}<small>{media.publication_state === "published" ? "Live-ready" : "Private"}</small></span>
                    </button>
                  ))}
                </div>
                <Link to="/admin/media"><ImagePlus aria-hidden="true" /> Add or refine an image</Link>
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="admin-menu-step">
              <div className="admin-panel-heading"><div><p className="admin-kicker">Step 02</p><h2 id="menu-step-title">Set price, visibility, and service.</h2></div><CheckCircle2 aria-hidden="true" /></div>
              <div className="admin-form-two-column">
                <TextField label="Base price (USD)" hint="Enter 14.50 for a $14.50 dish." min="0" step="0.01" type="number" value={minorToCurrencyInput(form.base_price_minor)} onChange={(event) => updateForm({ base_price_minor: currencyInputToMinor(event.target.value) })} />
                <TextField label="Introductory discount (USD)" hint="Enter 0 when there is no discount." min="0" step="0.01" type="number" value={minorToCurrencyInput(form.demo_discount_minor)} onChange={(event) => updateForm({ demo_discount_minor: currencyInputToMinor(event.target.value) })} />
              </div>
              <p className="admin-menu-price-preview">Customer price: <strong>{formatPrice(Math.max(0, form.base_price_minor - form.demo_discount_minor))}</strong></p>
              <div className="admin-form-two-column">
                <label className="admin-select-field">Customer menu<select value={form.publication_state} onChange={(event) => updateForm({ publication_state: event.target.value as PublicationState })}><option value="draft">Keep private while preparing</option><option value="published">Show on the customer menu</option></select></label>
                <TextField label="Menu position" hint="Use 0 to keep the current order. Smaller numbers appear earlier in this category." min="0" type="number" value={form.display_order} onChange={(event) => updateForm({ display_order: Number(event.target.value) })} />
              </div>
              <div className="admin-menu-service-card">
                <label className="admin-select-field">Service location<select value={form.location_id} onChange={(event) => updateForm({ location_id: event.target.value })}>{setup.locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label>
                <label className="admin-select-field">Availability<select value={form.availability_state} onChange={(event) => updateForm({ availability_state: event.target.value as AvailabilityState, available_from: "", available_until: "" })}><option value="available">Available now</option><option value="temporarily_unavailable">Pause for now</option><option value="scheduled">Schedule a window</option></select></label>
                {form.availability_state === "scheduled" ? <div className="admin-form-two-column"><TextField label="Starts" type="datetime-local" value={form.available_from} onChange={(event) => updateForm({ available_from: event.target.value })} /><TextField label="Ends" type="datetime-local" value={form.available_until} onChange={(event) => updateForm({ available_until: event.target.value })} /></div> : null}
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="admin-menu-step">
              <div className="admin-panel-heading"><div><p className="admin-kicker">Step 03</p><h2 id="menu-step-title">Make choices and care clear.</h2></div><FileText aria-hidden="true" /></div>
              <div className="admin-form-two-column"><TextField label="Ingredients" hint="Separate with commas. Customers will see this later in the menu flow." value={form.ingredients_text} onChange={(event) => updateForm({ ingredients_text: event.target.value })} /><TextField label="Dietary tags" hint="For example: vegetarian, gluten-aware." value={form.dietary_tags_text} onChange={(event) => updateForm({ dietary_tags_text: event.target.value })} /></div>
              <fieldset className="admin-allergen-grid"><legend>Allergen notes</legend><p>Select every known allergen. Leave clear only when none apply.</p><div>{setup.allergens.map((allergen) => <label key={allergen.id}><input checked={form.allergen_ids.includes(allergen.id)} type="checkbox" onChange={() => toggleAllergen(allergen.id)} /><span><strong>{allergen.name}</strong><small>{allergen.description}</small></span></label>)}</div></fieldset>
              <section className="admin-option-builder" aria-labelledby="option-builder-title">
                <div className="admin-panel-heading"><div><p className="admin-kicker">Customisation</p><h3 id="option-builder-title">Choice groups</h3></div><Button size="compact" variant="quiet" onClick={() => updateForm({ option_groups: [...form.option_groups, newOptionGroup()] })}><Plus aria-hidden="true" /> Add group</Button></div>
                <p>Use a required choice when a customer must select a base, side, or removal.</p>
                {form.option_groups.map((group, groupIndex) => (
                  <div key={group.id ?? `group-${groupIndex}`} className="admin-option-group">
                    <div className="admin-option-group-header"><strong>Group {groupIndex + 1}</strong><Button size="icon" variant="quiet" aria-label="Remove option group" onClick={() => updateForm({ option_groups: form.option_groups.filter((_, index) => index !== groupIndex) })}><Trash2 aria-hidden="true" /></Button></div>
                    <div className="admin-option-group-fields"><TextField label="Group name" value={group.name} onChange={(event) => updateGroup(groupIndex, { name: event.target.value })} /><label className="admin-select-field">How customers use it<select value={group.kind} onChange={(event) => updateGroup(groupIndex, { kind: event.target.value as OptionKind })}><option value="choice">Choose from options</option><option value="extra">Add an extra</option><option value="removal">Leave something out</option></select></label><TextField label="Required picks" min="0" type="number" value={group.minimum_selections} onChange={(event) => updateGroup(groupIndex, { minimum_selections: Number(event.target.value) })} /><TextField label="Maximum picks" min="0" type="number" value={group.maximum_selections} onChange={(event) => updateGroup(groupIndex, { maximum_selections: Number(event.target.value) })} /></div>
                    <div className="admin-option-list">{group.options.map((option, optionIndex) => <div key={option.id ?? `option-${optionIndex}`}><TextField label={`Option ${optionIndex + 1}`} value={option.name} onChange={(event) => updateOption(groupIndex, optionIndex, { name: event.target.value })} /><TextField label="Extra price (USD)" hint="Enter 0 when there is no extra charge." min="0" step="0.01" type="number" value={minorToCurrencyInput(option.price_delta_minor)} onChange={(event) => updateOption(groupIndex, optionIndex, { price_delta_minor: currencyInputToMinor(event.target.value) })} /><label className="admin-option-available"><input checked={option.is_available} type="checkbox" onChange={(event) => updateOption(groupIndex, optionIndex, { is_available: event.target.checked })} />Available</label><Button size="icon" variant="quiet" aria-label="Remove option" onClick={() => updateGroup(groupIndex, { options: group.options.filter((_, index) => index !== optionIndex) })}><Trash2 aria-hidden="true" /></Button></div>)}</div>
                    <Button size="compact" variant="quiet" onClick={() => updateGroup(groupIndex, { options: [...group.options, emptyOption()] })}><Plus aria-hidden="true" /> Add option</Button>
                  </div>
                ))}
              </section>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="admin-menu-step admin-menu-review">
              <div className="admin-panel-heading"><div><p className="admin-kicker">Step 04</p><h2 id="menu-step-title">Read it as your customer will.</h2></div><Eye aria-hidden="true" /></div>
              <dl><div><dt>Category</dt><dd>{selectedCategory?.name ?? "Not selected"}</dd></div><div><dt>Service</dt><dd>{form.availability_state === "temporarily_unavailable" ? "Paused" : form.availability_state === "scheduled" ? "Scheduled" : "Available now"}</dd></div><div><dt>Image</dt><dd>{selectedMedia?.original_filename ?? "Not selected"}</dd></div><div><dt>Allergens</dt><dd>{form.allergen_ids.length ? `${form.allergen_ids.length} noted` : "None noted"}</dd></div><div><dt>Options</dt><dd>{form.option_groups.length ? `${form.option_groups.length} groups` : "No customisation"}</dd></div></dl>
              <p className="admin-menu-review-note">Saving records this change. A customer-live dish appears in the public catalog API immediately; the customer menu screen itself is delivered in the next phase.</p>
            </div>
          ) : null}

          <footer className="admin-menu-step-actions">
            <Button disabled={step === 0} variant="quiet" onClick={() => setStep((current) => current - 1)}><ArrowLeft aria-hidden="true" /> Back</Button>
            {step < stepLabels.length - 1 ? <Button onClick={() => moveTo(step + 1)}>Continue <ArrowRight aria-hidden="true" /></Button> : <Button loading={saving} onClick={() => void saveItem()}><Save aria-hidden="true" /> Save dish</Button>}
          </footer>
        </section>

        <aside className="admin-menu-live-preview" aria-labelledby="menu-preview-title">
          <div className="admin-preview-label"><Eye aria-hidden="true" /> Customer card preview</div>
          <div className="admin-menu-preview-card">
            <ProtectedMediaImage alt={selectedMedia?.alt_text ?? "Selected dish"} mediaId={form.media_id || null} />
            <div><p>{selectedCategory?.name ?? "Menu category"}</p><h2 id="menu-preview-title">{form.name || "Your dish name"}</h2><span>{form.description || "A useful description will appear here."}</span><strong>{formatPrice(Math.max(0, form.base_price_minor - form.demo_discount_minor))}</strong>{form.demo_discount_minor > 0 ? <small>Includes demo discount</small> : null}</div>
          </div>
          <p>Preview reflects unsaved form values. Publishing requires a customer-live category and image.</p>
          {item?.history.length ? <div className="admin-history"><p>Recent recorded changes</p><ol>{item.history.map((change) => <li key={change.id}><span>{change.action.replaceAll("_", " ")}</span><strong>{change.actor_name}</strong><small>{displayTime(change.created_at)}</small></li>)}</ol></div> : null}
        </aside>
      </div>
    </div>
  );
}
