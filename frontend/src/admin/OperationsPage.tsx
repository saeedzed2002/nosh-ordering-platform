import {
  BadgePercent,
  Building2,
  ChartNoAxesCombined,
  FileSearch,
  Pencil,
  Power,
  RefreshCcw,
  Save,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "../components/ui/Button";
import { ApiError } from "./api";
import { useAdminSession } from "./session";

type OperationTab = "promotions" | "restaurant" | "customers" | "reports" | "audit";
type PromotionKind = "fixed_amount" | "percentage";
type Promotion = {
  id: string;
  code: string;
  name: string;
  kind: PromotionKind;
  discount_value: number;
  minimum_order_minor: number;
  starts_at: string | null;
  ends_at: string | null;
  usage_limit: number | null;
  usage_count: number;
  remaining_uses: number | null;
  is_active: boolean;
};
type OperatingHour = { weekday: number; opens_at: string | null; closes_at: string | null; is_closed: boolean };
type RestaurantSettings = {
  id: string;
  name: string;
  slug: string;
  address_text: string;
  contact_phone: string;
  pickup_instructions: string | null;
  delivery_area_text: string | null;
  pickup_available: boolean;
  delivery_available: boolean;
  preparation_minutes: number;
  demo_capacity: number;
  online_ordering_state: "on" | "timed_pause" | "off";
  online_ordering_paused_until: string | null;
  is_published: boolean;
  hours: OperatingHour[];
};
type CustomerOrder = { public_reference: string; status: string; fulfillment_method: string; total_minor: number; currency_code: string; created_at: string };
type Customer = { id: string; display_name: string; email: string; is_active: boolean; created_at: string; order_count: number; last_order_at: string | null; orders: CustomerOrder[] };
type AuditEvent = { id: string; created_at: string; actor_name: string; entity_type: string; entity_id: string | null; action: string; before_snapshot: Record<string, unknown>; after_snapshot: Record<string, unknown> };
type Report = {
  order_count: number;
  revenue_order_count: number;
  demo_revenue_minor: number;
  average_order_value_minor: number;
  popular_food: Array<{ menu_item_name: string; quantity: number; revenue_minor: number }>;
  status_distribution: Array<{ status: string; count: number }>;
  promotion_use: Array<{ code: string; uses: number; discount_minor: number }>;
  review_moderation: Array<{ status: string; count: number }>;
};

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const tabs: Array<{ value: OperationTab; label: string; icon: typeof BadgePercent }> = [
  { value: "promotions", label: "Promotions", icon: BadgePercent },
  { value: "restaurant", label: "Restaurant", icon: Building2 },
  { value: "customers", label: "Customers", icon: UsersRound },
  { value: "reports", label: "Reports", icon: ChartNoAxesCombined },
  { value: "audit", label: "Audit", icon: ShieldCheck },
];

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof ApiError ? reason.message : fallback;
}

function money(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value / 100);
}

function dateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function toDatetimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function toIso(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

function currencyInput(value: number): string {
  return (value / 100).toFixed(2);
}

function minorInput(value: string): number {
  return Math.max(0, Math.round(Number(value || "0") * 100));
}

type PromotionDraft = {
  code: string;
  name: string;
  kind: PromotionKind;
  discount: string;
  minimum: string;
  starts_at: string;
  ends_at: string;
  usage_limit: string;
  is_active: boolean;
};

function emptyPromotion(): PromotionDraft {
  return { code: "", name: "", kind: "percentage", discount: "10", minimum: "0", starts_at: "", ends_at: "", usage_limit: "", is_active: true };
}

function draftForPromotion(promotion: Promotion): PromotionDraft {
  return {
    code: promotion.code,
    name: promotion.name,
    kind: promotion.kind,
    discount: promotion.kind === "percentage" ? String(promotion.discount_value / 100) : currencyInput(promotion.discount_value),
    minimum: currencyInput(promotion.minimum_order_minor),
    starts_at: toDatetimeLocal(promotion.starts_at),
    ends_at: toDatetimeLocal(promotion.ends_at),
    usage_limit: promotion.usage_limit ? String(promotion.usage_limit) : "",
    is_active: promotion.is_active,
  };
}

function PromotionWorkspace() {
  const { request } = useAdminSession();
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [draft, setDraft] = useState<PromotionDraft>(emptyPromotion);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setPromotions(await request<Promotion[]>("/api/v1/admin/operations/promotions"));
  }, [request]);

  useEffect(() => {
    void load().catch((reason) => setError(errorMessage(reason, "Promotions could not be loaded."))).finally(() => setLoading(false));
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError(null);
    setNotice(null);
    const payload = {
      code: draft.code,
      name: draft.name,
      kind: draft.kind,
      discount_value: draft.kind === "percentage" ? Math.round(Number(draft.discount) * 100) : minorInput(draft.discount),
      minimum_order_minor: minorInput(draft.minimum),
      starts_at: toIso(draft.starts_at),
      ends_at: toIso(draft.ends_at),
      usage_limit: draft.usage_limit ? Number(draft.usage_limit) : null,
      is_active: draft.is_active,
    };
    try {
      const saved = await request<Promotion>(editingId ? `/api/v1/admin/operations/promotions/${editingId}` : "/api/v1/admin/operations/promotions", { method: editingId ? "PUT" : "POST", body: JSON.stringify(payload) });
      setPromotions((current) => editingId ? current.map((item) => item.id === saved.id ? saved : item) : [saved, ...current]);
      setNotice(editingId ? "Promotion updated." : "Promotion created.");
      setEditingId(null);
      setDraft(emptyPromotion());
    } catch (reason) {
      setError(errorMessage(reason, "The promotion could not be saved."));
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (promotion: Promotion) => {
    setError(null);
    try {
      const saved = await request<Promotion>(`/api/v1/admin/operations/promotions/${promotion.id}/deactivate`, { method: "POST" });
      setPromotions((current) => current.map((item) => item.id === saved.id ? saved : item));
      setNotice(`${saved.code} is no longer available at checkout.`);
    } catch (reason) {
      setError(errorMessage(reason, "The promotion could not be deactivated."));
    }
  };

  if (loading) return <p className="admin-inline-loading">Loading promotions…</p>;
  return <div className="operations-split"><section className="operations-form-card"><header><p className="admin-kicker">Checkout incentive</p><h2>{editingId ? "Edit promotion" : "Create a promotion"}</h2><p>Values are checked again by the server when an order is priced.</p></header><form onSubmit={(event) => { event.preventDefault(); void save(); }}><div className="admin-form-two-column"><label>Code<input required maxLength={48} value={draft.code} onChange={(event) => setDraft((current) => ({ ...current, code: event.target.value.toUpperCase() }))} /></label><label>Name<input required maxLength={160} value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} /></label><label>Discount type<select value={draft.kind} onChange={(event) => setDraft((current) => ({ ...current, kind: event.target.value as PromotionKind, discount: event.target.value === "percentage" ? "10" : "0.00" }))}><option value="percentage">Percentage</option><option value="fixed_amount">Fixed amount</option></select></label><label>{draft.kind === "percentage" ? "Percent off" : "Amount off (USD)"}<input required min="0.01" step="0.01" type="number" value={draft.discount} onChange={(event) => setDraft((current) => ({ ...current, discount: event.target.value }))} /></label><label>Minimum basket (USD)<input min="0" step="0.01" type="number" value={draft.minimum} onChange={(event) => setDraft((current) => ({ ...current, minimum: event.target.value }))} /></label><label>Usage limit <small>Optional</small><input min="1" type="number" value={draft.usage_limit} onChange={(event) => setDraft((current) => ({ ...current, usage_limit: event.target.value }))} /></label><label>Starts <small>Optional</small><input type="datetime-local" value={draft.starts_at} onChange={(event) => setDraft((current) => ({ ...current, starts_at: event.target.value }))} /></label><label>Ends <small>Optional</small><input type="datetime-local" value={draft.ends_at} onChange={(event) => setDraft((current) => ({ ...current, ends_at: event.target.value }))} /></label></div><label className="operations-check"><input checked={draft.is_active} type="checkbox" onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))} />Available to customers</label>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}{notice ? <p className="admin-form-notice">{notice}</p> : null}<footer><Button loading={saving} type="submit"><Save aria-hidden="true" />{editingId ? "Save promotion" : "Create promotion"}</Button>{editingId ? <Button variant="quiet" onClick={() => { setEditingId(null); setDraft(emptyPromotion()); }}>Cancel editing</Button> : null}</footer></form></section><section className="operations-list-card"><header><div><p className="admin-kicker">Current rules</p><h2>Promotions in this demo</h2></div><Button size="compact" variant="quiet" onClick={() => void load()}><RefreshCcw aria-hidden="true" />Refresh</Button></header>{promotions.length ? <div className="operations-promotion-list">{promotions.map((promotion) => <article key={promotion.id}><div><strong>{promotion.code}</strong><span className={promotion.is_active ? "operation-state active" : "operation-state"}>{promotion.is_active ? "Active" : "Inactive"}</span></div><h3>{promotion.name}</h3><p>{promotion.kind === "percentage" ? `${promotion.discount_value / 100}% off` : `${money(promotion.discount_value)} off`} · minimum {money(promotion.minimum_order_minor)}</p><small>{promotion.usage_count} uses{promotion.remaining_uses === null ? "" : ` · ${promotion.remaining_uses} remaining`} · {promotion.starts_at ? `starts ${dateTime(promotion.starts_at)}` : "starts now"}</small><footer><Button size="compact" variant="quiet" onClick={() => { setEditingId(promotion.id); setDraft(draftForPromotion(promotion)); }}> <Pencil aria-hidden="true" />Edit</Button>{promotion.is_active ? <Button size="compact" variant="secondary" onClick={() => void deactivate(promotion)}><Power aria-hidden="true" />Deactivate</Button> : null}</footer></article>)}</div> : <p className="admin-empty-state">No promotions are configured.</p>}</section></div>;
}

function RestaurantWorkspace() {
  const { request } = useAdminSession();
  const [locations, setLocations] = useState<RestaurantSettings[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState<RestaurantSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void request<RestaurantSettings[]>("/api/v1/admin/operations/settings").then((next) => { setLocations(next); setSelectedId(next[0]?.id ?? ""); setDraft(next[0] ?? null); }).catch((reason) => setError(errorMessage(reason, "Restaurant settings could not be loaded.")));
  }, [request]);

  const selectLocation = (id: string) => { setSelectedId(id); setDraft(locations.find((location) => location.id === id) ?? null); setNotice(null); };
  const save = async () => {
    if (!draft) return;
    setSaving(true); setError(null); setNotice(null);
    try {
      const payload = { ...draft, online_ordering_paused_until: toIso(toDatetimeLocal(draft.online_ordering_paused_until)), hours: draft.hours.map((hour) => ({ ...hour, opens_at: hour.opens_at ? hour.opens_at.slice(0, 5) : null, closes_at: hour.closes_at ? hour.closes_at.slice(0, 5) : null })) };
      const saved = await request<RestaurantSettings>(`/api/v1/admin/operations/settings/${draft.id}`, { method: "PUT", body: JSON.stringify(payload) });
      setLocations((current) => current.map((location) => location.id === saved.id ? saved : location)); setDraft(saved); setNotice("Restaurant settings saved. The customer ordering rules now use these values.");
    } catch (reason) { setError(errorMessage(reason, "Restaurant settings could not be saved.")); } finally { setSaving(false); }
  };
  if (!draft) return <p className={error ? "admin-form-error" : "admin-inline-loading"}>{error ?? "Loading restaurant settings…"}</p>;
  return <section className="operations-form-card operations-restaurant"><header><p className="admin-kicker">Restaurant operations</p><h2>Set the local service rules.</h2><p>Hours, fulfillment methods, preparation time, capacity, and ordering state are enforced outside this form too.</p></header><div className="operations-location-picker"><label>Location<select value={selectedId} onChange={(event) => selectLocation(event.target.value)}>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label><span>{draft.slug}</span></div><form onSubmit={(event) => { event.preventDefault(); void save(); }}><div className="admin-form-two-column"><label>Restaurant name<input required value={draft.name} onChange={(event) => setDraft((current) => current ? { ...current, name: event.target.value } : current)} /></label><label>Contact phone<input required value={draft.contact_phone} onChange={(event) => setDraft((current) => current ? { ...current, contact_phone: event.target.value } : current)} /></label></div><label>Address<textarea required value={draft.address_text} onChange={(event) => setDraft((current) => current ? { ...current, address_text: event.target.value } : current)} /></label><div className="admin-form-two-column"><label>Pickup instructions<textarea value={draft.pickup_instructions ?? ""} onChange={(event) => setDraft((current) => current ? { ...current, pickup_instructions: event.target.value || null } : current)} /></label><label>Delivery area<textarea value={draft.delivery_area_text ?? ""} onChange={(event) => setDraft((current) => current ? { ...current, delivery_area_text: event.target.value || null } : current)} /></label></div><div className="operations-check-row"><label className="operations-check"><input checked={draft.pickup_available} type="checkbox" onChange={(event) => setDraft((current) => current ? { ...current, pickup_available: event.target.checked } : current)} />Pickup available</label><label className="operations-check"><input checked={draft.delivery_available} type="checkbox" onChange={(event) => setDraft((current) => current ? { ...current, delivery_available: event.target.checked } : current)} />Delivery available</label><label className="operations-check"><input checked={draft.is_published} type="checkbox" onChange={(event) => setDraft((current) => current ? { ...current, is_published: event.target.checked } : current)} />Visible to customers</label></div><div className="admin-form-two-column"><label>Ordering state<select value={draft.online_ordering_state} onChange={(event) => setDraft((current) => current ? { ...current, online_ordering_state: event.target.value as RestaurantSettings["online_ordering_state"], online_ordering_paused_until: event.target.value === "timed_pause" ? current.online_ordering_paused_until : null } : current)}><option value="on">On</option><option value="timed_pause">Timed pause</option><option value="off">Off</option></select></label>{draft.online_ordering_state === "timed_pause" ? <label>Pause ends<input required type="datetime-local" value={toDatetimeLocal(draft.online_ordering_paused_until)} onChange={(event) => setDraft((current) => current ? { ...current, online_ordering_paused_until: toIso(event.target.value) } : current)} /></label> : <span /> }<label>Preparation minutes<input min="0" max="240" required type="number" value={draft.preparation_minutes} onChange={(event) => setDraft((current) => current ? { ...current, preparation_minutes: Number(event.target.value) } : current)} /></label><label>Active-order capacity<input min="0" max="10000" required type="number" value={draft.demo_capacity} onChange={(event) => setDraft((current) => current ? { ...current, demo_capacity: Number(event.target.value) } : current)} /></label></div><fieldset className="operations-hours"><legend>Opening hours</legend><div>{[...draft.hours].sort((left, right) => left.weekday - right.weekday).map((hour) => <article key={hour.weekday}><strong>{weekdays[hour.weekday]}</strong><label className="operations-check"><input checked={!hour.is_closed} type="checkbox" onChange={(event) => setDraft((current) => current ? { ...current, hours: current.hours.map((item) => item.weekday === hour.weekday ? { ...item, is_closed: !event.target.checked, opens_at: event.target.checked ? item.opens_at ?? "12:00" : null, closes_at: event.target.checked ? item.closes_at ?? "21:00" : null } : item) } : current)} />Open</label><label>From<input disabled={hour.is_closed} type="time" value={hour.opens_at?.slice(0, 5) ?? ""} onChange={(event) => setDraft((current) => current ? { ...current, hours: current.hours.map((item) => item.weekday === hour.weekday ? { ...item, opens_at: event.target.value || null } : item) } : current)} /></label><label>To<input disabled={hour.is_closed} type="time" value={hour.closes_at?.slice(0, 5) ?? ""} onChange={(event) => setDraft((current) => current ? { ...current, hours: current.hours.map((item) => item.weekday === hour.weekday ? { ...item, closes_at: event.target.value || null } : item) } : current)} /></label></article>)}</div></fieldset>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}{notice ? <p className="admin-form-notice">{notice}</p> : null}<Button loading={saving} type="submit"><Save aria-hidden="true" />Save restaurant settings</Button></form></section>;
}

function CustomersWorkspace() {
  const { request, session } = useAdminSession();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isOwner = session?.user.role === "owner";
  const load = useCallback(async (phrase = "") => { const params = phrase.trim() ? `?query=${encodeURIComponent(phrase.trim())}` : ""; const next = await request<Customer[]>(`/api/v1/admin/operations/customers${params}`); setCustomers(next); }, [request]);
  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason, "Customers could not be loaded."))).finally(() => setLoading(false)); }, [load]);
  const selectCustomer = async (customer: Customer) => { setError(null); try { setSelected(await request<Customer>(`/api/v1/admin/operations/customers/${customer.id}`)); } catch (reason) { setError(errorMessage(reason, "Customer history could not be loaded.")); } };
  const toggleState = async () => { if (!selected) return; setError(null); try { const saved = await request<Customer>(`/api/v1/admin/operations/customers/${selected.id}/state`, { method: "PATCH", body: JSON.stringify({ is_active: !selected.is_active }) }); setSelected(saved); setCustomers((current) => current.map((customer) => customer.id === saved.id ? { ...customer, ...saved, orders: [] } : customer)); } catch (reason) { setError(errorMessage(reason, "Customer account state could not be changed.")); } };
  if (loading) return <p className="admin-inline-loading">Loading customers…</p>;
  return <div className="operations-split customers-workspace"><section className="operations-list-card"><header><div><p className="admin-kicker">Customer accounts</p><h2>Find an account without exposing private profile data.</h2></div></header><form className="operations-search" onSubmit={(event) => { event.preventDefault(); void load(query); }}><input aria-label="Search customers" placeholder="Name or email" value={query} onChange={(event) => setQuery(event.target.value)} /><Button size="compact" type="submit"><FileSearch aria-hidden="true" />Search</Button></form>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}<div className="operations-customer-list">{customers.map((customer) => <button key={customer.id} className={selected?.id === customer.id ? "selected" : ""} type="button" onClick={() => void selectCustomer(customer)}><span><strong>{customer.display_name}</strong><small>{customer.email}</small></span><span><small>{customer.order_count} orders</small><em className={customer.is_active ? "operation-state active" : "operation-state"}>{customer.is_active ? "Active" : "Inactive"}</em></span></button>)}{!customers.length ? <p className="admin-empty-state">No customer account matches that search.</p> : null}</div></section><section className="operations-detail-card">{selected ? <><header><p className="admin-kicker">Account summary</p><h2>{selected.display_name}</h2><p>{selected.email} · joined {dateTime(selected.created_at)}</p></header><dl><div><dt>Account state</dt><dd>{selected.is_active ? "Active" : "Inactive"}</dd></div><div><dt>Orders</dt><dd>{selected.order_count}</dd></div><div><dt>Last order</dt><dd>{dateTime(selected.last_order_at)}</dd></div></dl>{isOwner ? <Button variant={selected.is_active ? "danger" : "primary"} onClick={() => void toggleState()}>{selected.is_active ? <><Power aria-hidden="true" />Deactivate account</> : <><Power aria-hidden="true" />Activate account</>}</Button> : <p className="operations-role-note">Only an owner can change account state.</p>}<section className="operations-order-history"><h3>Recent orders</h3>{selected.orders.length ? selected.orders.map((order) => <article key={order.public_reference}><strong>{order.public_reference}</strong><span>{order.status.replaceAll("_", " ")} · {money(order.total_minor, order.currency_code)}</span><small>{dateTime(order.created_at)} · {order.fulfillment_method}</small></article>) : <p>No orders are attached to this account.</p>}</section></> : <p className="admin-empty-state">Select a customer to see order history and account state.</p>}</section></div>;
}

function ReportsWorkspace() {
  const { request } = useAdminSession();
  const [report, setReport] = useState<Report | null>(null);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async (start = startsAt, end = endsAt) => { const params = new URLSearchParams(); if (start) params.set("starts_at", `${start}T00:00:00Z`); if (end) { const next = new Date(`${end}T00:00:00Z`); next.setUTCDate(next.getUTCDate() + 1); params.set("ends_at", next.toISOString()); } const suffix = params.size ? `?${params.toString()}` : ""; setReport(await request<Report>(`/api/v1/admin/operations/reports${suffix}`)); }, [endsAt, request, startsAt]);
  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason, "Reports could not be loaded."))).finally(() => setLoading(false)); }, [load]);
  if (loading) return <p className="admin-inline-loading">Building report…</p>;
  return <section className="operations-reports"><header className="operations-section-heading"><div><p className="admin-kicker">Local demo reporting</p><h2>Read the actual orders, not an estimate.</h2><p>Revenue excludes declined and cancelled orders. A date range includes its final day.</p></div><form onSubmit={(event) => { event.preventDefault(); void load(); }}><label>From<input type="date" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label><label>To<input type="date" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} /></label><Button size="compact" type="submit"><RefreshCcw aria-hidden="true" />Run report</Button></form></header>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}{report ? <><div className="operations-metrics"><article><span>Orders</span><strong>{report.order_count}</strong><small>{report.revenue_order_count} count toward revenue</small></article><article><span>Demo revenue</span><strong>{money(report.demo_revenue_minor)}</strong><small>Confirmed local-demo orders</small></article><article><span>Average order</span><strong>{money(report.average_order_value_minor)}</strong><small>Revenue divided by confirmed orders</small></article></div><div className="operations-report-grid"><section><h3>Popular food</h3>{report.popular_food.length ? report.popular_food.map((item) => <article key={item.menu_item_name}><strong>{item.menu_item_name}</strong><span>{item.quantity} sold · {money(item.revenue_minor)}</span></article>) : <p>No order lines in this range.</p>}</section><section><h3>Order status</h3>{report.status_distribution.length ? report.status_distribution.map((item) => <article key={item.status}><strong>{item.status.replaceAll("_", " ")}</strong><span>{item.count}</span></article>) : <p>No orders in this range.</p>}</section><section><h3>Promotion use</h3>{report.promotion_use.length ? report.promotion_use.map((item) => <article key={item.code}><strong>{item.code}</strong><span>{item.uses} uses · {money(item.discount_minor)} discounted</span></article>) : <p>No promotion was applied.</p>}</section><section><h3>Review moderation</h3>{report.review_moderation.length ? report.review_moderation.map((item) => <article key={item.status}><strong>{item.status}</strong><span>{item.count}</span></article>) : <p>No review activity in this range.</p>}</section></div></> : null}</section>;
}

function AuditWorkspace() {
  const { request, session } = useAdminSession();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const isOwner = session?.user.role === "owner";
  const load = useCallback(async () => { setEvents(await request<AuditEvent[]>("/api/v1/admin/operations/audit")); }, [request]);
  useEffect(() => { if (isOwner) void load().catch((reason) => setError(errorMessage(reason, "Audit history could not be loaded."))); }, [isOwner, load]);
  if (!isOwner) return <section className="operations-detail-card"><p className="admin-kicker">Owner-only history</p><h2>Audit events stay restricted.</h2><p>Managers can operate the restaurant; only the owner can inspect safe before-and-after metadata for sensitive changes.</p></section>;
  return <section className="operations-audit"><header><div><p className="admin-kicker">Sensitive-write history</p><h2>Every change has a trace.</h2><p>Snapshots exclude passwords, tokens, customer addresses, and payment details.</p></div><Button size="compact" variant="quiet" onClick={() => void load()}><RefreshCcw aria-hidden="true" />Refresh</Button></header>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}<div>{events.length ? events.map((event) => <article key={event.id}><header><strong>{event.entity_type.replaceAll("_", " ")} · {event.action.replaceAll("_", " ")}</strong><time dateTime={event.created_at}>{dateTime(event.created_at)}</time></header><p>By {event.actor_name}</p><dl><div><dt>Before</dt><dd><code>{JSON.stringify(event.before_snapshot)}</code></dd></div><div><dt>After</dt><dd><code>{JSON.stringify(event.after_snapshot)}</code></dd></div></dl></article>) : <p className="admin-empty-state">No sensitive admin changes have been recorded yet.</p>}</div></section>;
}

export function OperationsPage() {
  const [tab, setTab] = useState<OperationTab>("promotions");
  const activeTab = useMemo(() => tabs.find((item) => item.value === tab), [tab]);
  return <div className="admin-operations"><header className="admin-page-heading"><div><p className="admin-kicker">Operations control room</p><h1>Run the local restaurant without developer tools.</h1><p>Manage the customer-facing rules, account safety, and evidence for decisions in one place.</p></div><div className="operations-heading-mark">{activeTab ? <activeTab.icon aria-hidden="true" /> : null}<span>{activeTab?.label}</span></div></header><nav className="operations-tabs" aria-label="Operations workspace">{tabs.map((item) => { const Icon = item.icon; return <button key={item.value} aria-current={tab === item.value ? "page" : undefined} className={tab === item.value ? "active" : ""} onClick={() => setTab(item.value)} type="button"><Icon aria-hidden="true" />{item.label}</button>; })}</nav>{tab === "promotions" ? <PromotionWorkspace /> : null}{tab === "restaurant" ? <RestaurantWorkspace /> : null}{tab === "customers" ? <CustomersWorkspace /> : null}{tab === "reports" ? <ReportsWorkspace /> : null}{tab === "audit" ? <AuditWorkspace /> : null}</div>;
}
