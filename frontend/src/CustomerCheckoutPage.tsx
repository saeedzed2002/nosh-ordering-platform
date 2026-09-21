import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Clock3,
  LoaderCircle,
  MapPin,
  ReceiptText,
  ShoppingBag,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "./components/ui/Button";
import { CustomerSiteFooter, CustomerSiteHeader } from "./CustomerMenuPage";
import { useCustomerCart } from "./customerCart";
import {
  readCustomerOrder,
  submitCustomerOrder,
  type CustomerFulfillmentMethod,
  type CustomerOrderReceipt,
  type CustomerPaymentScenario,
} from "./customerCheckout";
import { formatCustomerPrice, useCustomerCatalog } from "./customerCatalog";

type CheckoutForm = {
  deliveryAddress: string;
  fulfillmentInstructions: string;
  fulfillmentMethod: CustomerFulfillmentMethod;
  locationSlug: string;
  paymentScenario: CustomerPaymentScenario;
  promotionCode: string;
  recipientEmail: string;
  recipientName: string;
  recipientPhone: string;
  scheduledFor: string;
  timing: "immediate" | "scheduled";
};

const initialForm: CheckoutForm = {
  deliveryAddress: "",
  fulfillmentInstructions: "",
  fulfillmentMethod: "pickup",
  locationSlug: "",
  paymentScenario: "succeeds",
  promotionCode: "WELCOME10",
  recipientEmail: "",
  recipientName: "",
  recipientPhone: "",
  scheduledFor: "",
  timing: "immediate",
};
const emptyLocations = [] as const;

function checkoutIdempotencyKey(): string {
  const value = globalThis.crypto?.randomUUID?.().replaceAll("-", "");
  return `checkout-${value ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
}

function formatMoment(value: string | null): string {
  if (!value) {
    return "As soon as the kitchen can prepare it";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function ReceiptLines({ receipt }: { receipt: CustomerOrderReceipt }) {
  return (
    <ul className="customer-receipt-lines">
      {receipt.lines.map((line, index) => (
        <li key={`${line.menu_item_slug}-${line.note ?? "standard"}-${index}`}>
          <div>
            <strong>{line.quantity} × {line.menu_item_name}</strong>
            {line.selected_options.length ? <span>{line.selected_options.map((option) => option.name).join(", ")}</span> : null}
            {line.note ? <span>Kitchen note: {line.note}</span> : null}
          </div>
          <strong>{formatCustomerPrice(line.line_total_minor, line.currency_code)}</strong>
        </li>
      ))}
    </ul>
  );
}

function CheckoutSummary() {
  const { quote } = useCustomerCart();
  if (!quote) {
    return null;
  }
  return (
    <aside className="customer-checkout-summary" aria-live="polite">
      <p className="eyebrow">Kitchen-checked cart</p>
      <strong>{formatCustomerPrice(quote.subtotal_minor, quote.currency_code)}</strong>
      <p>This subtotal is recalculated from the live kitchen menu. The final total, including any eligible promotion, is shown before the receipt is saved.</p>
      <dl>
        <div><dt>Food and choices</dt><dd>{formatCustomerPrice(quote.subtotal_minor, quote.currency_code)}</dd></div>
        <div><dt>Delivery fee</dt><dd>Included in this local demo</dd></div>
        <div><dt>Promotion</dt><dd>Validated by the kitchen</dd></div>
      </dl>
      <small>No card number, cardholder name, or payment account is collected here.</small>
    </aside>
  );
}

export function CustomerCheckoutPage() {
  const { clearCart, isUpdating, lines, quote } = useCustomerCart();
  const { data: snapshot, status } = useCustomerCatalog();
  const navigate = useNavigate();
  const [form, setForm] = useState<CheckoutForm>(initialForm);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const idempotencyKey = useRef(checkoutIdempotencyKey());
  const locations = snapshot?.locations ?? emptyLocations;
  const selectedLocation = useMemo(
    () => locations.find((location) => location.slug === form.locationSlug) ?? null,
    [form.locationSlug, locations],
  );

  useEffect(() => {
    if (!form.locationSlug && locations[0]) {
      setForm((current) => ({ ...current, locationSlug: locations[0].slug }));
    }
  }, [form.locationSlug, locations]);

  const updateForm = <Key extends keyof CheckoutForm>(key: Key, value: CheckoutForm[Key]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const currentMethodIsAvailable = form.fulfillmentMethod === "pickup"
    ? selectedLocation?.pickup_available
    : selectedLocation?.delivery_available;
  const canSubmit = Boolean(
    quote && lines.length && selectedLocation && currentMethodIsAvailable && !isUpdating && !isSubmitting,
  );

  const placeOrder = async () => {
    if (!quote || !lines.length || !selectedLocation || !currentMethodIsAvailable) {
      setSubmitError("Your cart or fulfilment details need attention before this order can be placed.");
      return;
    }
    if (form.timing === "scheduled" && !form.scheduledFor) {
      setSubmitError("Choose a scheduled time before placing this order.");
      return;
    }
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const receipt = await submitCustomerOrder(
        {
          idempotency_key: idempotencyKey.current,
          location_slug: selectedLocation.slug,
          fulfillment_method: form.fulfillmentMethod,
          timing: form.timing,
          scheduled_for: form.timing === "scheduled" ? new Date(form.scheduledFor).toISOString() : null,
          recipient_name: form.recipientName,
          recipient_email: form.recipientEmail,
          recipient_phone: form.recipientPhone,
          delivery_address: form.fulfillmentMethod === "delivery" ? form.deliveryAddress : null,
          fulfillment_instructions: form.fulfillmentInstructions || null,
          promotion_code: form.promotionCode || null,
          payment_scenario: form.paymentScenario,
          lines,
        },
        new AbortController().signal,
      );
      clearCart();
      navigate(`/orders/${receipt.public_reference}`, { replace: true });
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "The local kitchen could not place this order.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-shell customer-checkout-page">
      <a className="skip-link" href="#checkout-form">Skip to checkout form</a>
      <CustomerSiteHeader />
      <main>
        <header className="customer-checkout-hero">
          <Link className="customer-back-link" to="/menu"><ArrowLeft aria-hidden="true" /> Back to menu</Link>
          <p className="eyebrow">Local checkout</p>
          <h1>One last clear step.</h1>
          <p>Choose how this order should be fulfilled, then the kitchen saves an immutable receipt with its current price and choices.</p>
        </header>

        {!lines.length ? <section className="customer-checkout-empty"><ShoppingBag aria-hidden="true" /><h2>Your cart is empty.</h2><p>Add a dish and its choices before coming back to checkout.</p><Link className="nosh-button" data-size="default" data-variant="primary" to="/menu">Browse menu</Link></section> : null}

        {lines.length ? <section className="customer-checkout-workspace">
          <form id="checkout-form" className="customer-checkout-form" onSubmit={(event) => { event.preventDefault(); void placeOrder(); }}>
            <fieldset disabled={isSubmitting}>
              <legend>Kitchen location</legend>
              <p>Choose where the kitchen will prepare this order.</p>
              <label className="customer-checkout-field">Location
                <select required value={form.locationSlug} onChange={(event) => updateForm("locationSlug", event.target.value)}>
                  <option value="" disabled>Select a location</option>
                  {locations.map((location) => <option key={location.id} value={location.slug}>{location.name}</option>)}
                </select>
              </label>
              {status === "loading" ? <small>Loading locations…</small> : null}
              {selectedLocation ? <p className="customer-checkout-location-note"><MapPin aria-hidden="true" /> {selectedLocation.address_text} · About {selectedLocation.preparation_minutes} min</p> : null}
            </fieldset>

            <fieldset disabled={isSubmitting || !selectedLocation}>
              <legend>How should it arrive?</legend>
              <div className="customer-checkout-options">
                <label className={form.fulfillmentMethod === "pickup" ? "selected" : undefined}>
                  <input checked={form.fulfillmentMethod === "pickup"} disabled={!selectedLocation?.pickup_available} name="fulfillment-method" type="radio" value="pickup" onChange={() => updateForm("fulfillmentMethod", "pickup")} />
                  <span><strong>Pickup</strong><small>{selectedLocation?.pickup_available ? selectedLocation.pickup_instructions ?? "Collect from the kitchen." : "Unavailable at this location"}</small></span>
                </label>
                <label className={form.fulfillmentMethod === "delivery" ? "selected" : undefined}>
                  <input checked={form.fulfillmentMethod === "delivery"} disabled={!selectedLocation?.delivery_available} name="fulfillment-method" type="radio" value="delivery" onChange={() => updateForm("fulfillmentMethod", "delivery")} />
                  <span><strong>Delivery</strong><small>{selectedLocation?.delivery_available ? selectedLocation.delivery_area_text ?? "Available in the local demo area." : "Unavailable at this location"}</small></span>
                </label>
              </div>
              {!currentMethodIsAvailable ? <small className="customer-checkout-error">Choose an available fulfilment method.</small> : null}
            </fieldset>

            <fieldset disabled={isSubmitting}>
              <legend>When should it be prepared?</legend>
              <div className="customer-checkout-options">
                <label className={form.timing === "immediate" ? "selected" : undefined}><input checked={form.timing === "immediate"} name="timing" type="radio" onChange={() => updateForm("timing", "immediate")} /><span><strong>As soon as possible</strong><small>Prepared in the current kitchen window.</small></span></label>
                <label className={form.timing === "scheduled" ? "selected" : undefined}><input checked={form.timing === "scheduled"} name="timing" type="radio" onChange={() => updateForm("timing", "scheduled")} /><span><strong>Schedule it</strong><small>Choose a future local time.</small></span></label>
              </div>
              {form.timing === "scheduled" ? <label className="customer-checkout-field">Scheduled time<input required min={new Date().toISOString().slice(0, 16)} type="datetime-local" value={form.scheduledFor} onChange={(event) => updateForm("scheduledFor", event.target.value)} /></label> : null}
            </fieldset>

            <fieldset disabled={isSubmitting}>
              <legend>Who is this for?</legend>
              <div className="customer-checkout-fields-grid">
                <label className="customer-checkout-field">Name<input required autoComplete="name" maxLength={120} minLength={2} value={form.recipientName} onChange={(event) => updateForm("recipientName", event.target.value)} /></label>
                <label className="customer-checkout-field">Phone<input required autoComplete="tel" inputMode="tel" maxLength={30} minLength={7} value={form.recipientPhone} onChange={(event) => updateForm("recipientPhone", event.target.value)} /></label>
              </div>
              <label className="customer-checkout-field">Email<input required autoComplete="email" maxLength={320} type="email" value={form.recipientEmail} onChange={(event) => updateForm("recipientEmail", event.target.value)} /></label>
              {form.fulfillmentMethod === "delivery" ? <label className="customer-checkout-field">Delivery address<textarea required maxLength={500} value={form.deliveryAddress} onChange={(event) => updateForm("deliveryAddress", event.target.value)} /></label> : null}
              <label className="customer-checkout-field">Instructions for the kitchen<textarea maxLength={500} placeholder="Optional: access, pickup, or kitchen note" value={form.fulfillmentInstructions} onChange={(event) => updateForm("fulfillmentInstructions", event.target.value)} /></label>
            </fieldset>

            <fieldset disabled={isSubmitting}>
              <legend>Promotion and local payment simulation</legend>
              <label className="customer-checkout-field">Promotion code<input maxLength={48} value={form.promotionCode} onChange={(event) => updateForm("promotionCode", event.target.value)} /></label>
              <p>This demo includes WELCOME10 for eligible orders. The server decides whether any promotion applies.</p>
              <div className="customer-checkout-options customer-payment-options">
                <label className={form.paymentScenario === "succeeds" ? "selected" : undefined}><input checked={form.paymentScenario === "succeeds"} name="payment-scenario" type="radio" onChange={() => updateForm("paymentScenario", "succeeds")} /><span><strong>Approve local mock payment</strong><small>No external payment provider or card data is used.</small></span></label>
                <label className={form.paymentScenario === "fails" ? "selected" : undefined}><input checked={form.paymentScenario === "fails"} name="payment-scenario" type="radio" onChange={() => updateForm("paymentScenario", "fails")} /><span><strong>Simulate a declined payment</strong><small>Tests the recoverable failure state without saving an order.</small></span></label>
              </div>
            </fieldset>

            {submitError ? <p className="customer-checkout-error" role="alert">{submitError}</p> : null}
            <Button disabled={!canSubmit} loading={isSubmitting} type="submit">Place local-demo order <ReceiptText aria-hidden="true" /></Button>
          </form>
          <CheckoutSummary />
        </section> : null}
      </main>
      <CustomerSiteFooter />
    </div>
  );
}

export function CustomerOrderConfirmationPage() {
  const { publicReference } = useParams();
  const [receipt, setReceipt] = useState<CustomerOrderReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!publicReference) {
      setError("An order reference is required to open this receipt.");
      return;
    }
    const controller = new AbortController();
    setReceipt(null);
    setError(null);
    void readCustomerOrder(publicReference, controller.signal)
      .then((nextReceipt) => {
        if (!controller.signal.aborted) {
          setReceipt(nextReceipt);
        }
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : "This receipt could not be opened.");
        }
      });
    return () => controller.abort();
  }, [attempt, publicReference]);

  return (
    <div className="app-shell customer-confirmation-page">
      <CustomerSiteHeader />
      <main>
        {!receipt && !error ? <section className="customer-receipt-loading"><LoaderCircle aria-hidden="true" /><p>Opening your saved order receipt…</p></section> : null}
        {error ? <section className="customer-checkout-empty" role="alert"><CircleAlert aria-hidden="true" /><h1>This order receipt could not be opened.</h1><p>{error}</p><Button variant="secondary" onClick={() => setAttempt((current) => current + 1)}>Try again</Button><Link className="nosh-button" data-size="default" data-variant="primary" to="/menu">Back to menu</Link></section> : null}
        {receipt ? <section className="customer-receipt">
          <header><p className="eyebrow"><CheckCircle2 aria-hidden="true" /> Local-demo order confirmed</p><h1>Your order is with the kitchen.</h1><p>The kitchen has saved the price, selected choices, fulfilment details, and confirmation below. Refreshing this page reads the same receipt without exposing private contact or address data.</p></header>
          <div className="customer-receipt-workspace">
            <section className="customer-receipt-card">
              <div className="customer-receipt-reference"><span>Order reference</span><strong>{receipt.public_reference}</strong><small>{receipt.status === "scheduled" ? "Scheduled" : "Submitted"} · {formatMoment(receipt.scheduled_for ?? receipt.created_at)}</small></div>
              <ReceiptLines receipt={receipt} />
              <dl className="customer-receipt-totals"><div><dt>Subtotal</dt><dd>{formatCustomerPrice(receipt.subtotal_minor, receipt.currency_code)}</dd></div>{receipt.promotion_discount_minor ? <div><dt>{receipt.promotion_code ?? "Promotion"}</dt><dd>−{formatCustomerPrice(receipt.promotion_discount_minor, receipt.currency_code)}</dd></div> : null}<div className="total"><dt>Total</dt><dd>{formatCustomerPrice(receipt.total_minor, receipt.currency_code)}</dd></div></dl>
              <p className="customer-receipt-payment">{receipt.payment_message}</p>
            </section>
            <aside className="customer-receipt-details"><div><MapPin aria-hidden="true" /><span>From</span><strong>{receipt.location_name}</strong><p>{receipt.location_address}</p></div><div><Clock3 aria-hidden="true" /><span>{receipt.fulfillment_method === "delivery" ? "Delivery" : "Pickup"}</span><strong>{receipt.fulfillment_method === "delivery" ? "Delivery details saved with the kitchen" : "Collect from the kitchen counter"}</strong><p>Private address and instruction details are not shown on this public receipt.</p></div><div><ReceiptText aria-hidden="true" /><span>Contact</span><strong>Contact details saved</strong><p>Private recipient information is not shown on this public receipt.</p></div></aside>
          </div>
          <Link className="nosh-button" data-size="default" data-variant="primary" to="/menu">Return to menu</Link>
        </section> : null}
      </main>
      <CustomerSiteFooter />
    </div>
  );
}
