import {
  Archive,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  LoaderCircle,
  MapPin,
  PackageCheck,
  Search,
  SlidersHorizontal,
  Truck,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "../components/ui/Button";
import { ApiError } from "./api";
import {
  formatOrderDeskMoment,
  formatOrderDeskPrice,
  issueReasons,
  orderActionLabel,
  orderStatusLabel,
  type AdminFulfillmentMethod,
  type AdminOrderDesk,
  type AdminOrderDetail,
  type AdminOrderQueue,
  type AdminOrderStatus,
  type LocationOrderControls,
  type OnlineOrderingState,
  type OrderIssueReason,
} from "./orderDeskTypes";
import { useAdminSession } from "./session";

const queues: Array<{ label: string; value: "all" | AdminOrderQueue }> = [
  { value: "all", label: "All orders" },
  { value: "needs_approval", label: "Needs approval" },
  { value: "scheduled", label: "Scheduled" },
  { value: "active", label: "Active" },
  { value: "ready", label: "Ready" },
  { value: "completed", label: "Completed" },
  { value: "archive", label: "Archive" },
];

const statuses: AdminOrderStatus[] = [
  "scheduled",
  "submitted",
  "accepted",
  "preparing",
  "ready_for_pickup",
  "ready_for_courier",
  "handed_to_customer",
  "handed_to_courier",
  "out_for_delivery",
  "delivered",
  "needs_contact",
  "declined",
  "cancelled",
];

const issueStatuses = new Set<AdminOrderStatus>(["needs_contact", "declined", "cancelled"]);
const sensitiveStatuses = new Set<AdminOrderStatus>(["declined", "cancelled"]);

type ControlsDraft = {
  demo_capacity: number;
  online_ordering_paused_until: string;
  online_ordering_state: OnlineOrderingState;
  preparation_minutes: number;
};

function formatDatetimeLocal(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function draftFromControls(controls: LocationOrderControls): ControlsDraft {
  return {
    online_ordering_state: controls.online_ordering_state,
    online_ordering_paused_until: formatDatetimeLocal(controls.online_ordering_paused_until),
    preparation_minutes: controls.preparation_minutes,
    demo_capacity: controls.demo_capacity,
  };
}

function statusClass(status: AdminOrderStatus): string {
  if (status === "declined" || status === "cancelled" || status === "needs_contact") {
    return "issue";
  }
  if (status === "ready_for_pickup" || status === "ready_for_courier") {
    return "ready";
  }
  if (status === "delivered" || status === "handed_to_customer") {
    return "complete";
  }
  return "active";
}

export function OrderDeskPage() {
  const { request, session } = useAdminSession();
  const [desk, setDesk] = useState<AdminOrderDesk | null>(null);
  const [controls, setControls] = useState<LocationOrderControls[]>([]);
  const [selectedReference, setSelectedReference] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminOrderDetail | null>(null);
  const [selectedControlsId, setSelectedControlsId] = useState("");
  const [controlsDraft, setControlsDraft] = useState<ControlsDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [savingTransition, setSavingTransition] = useState<AdminOrderStatus | null>(null);
  const [savingControls, setSavingControls] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingIssue, setPendingIssue] = useState<AdminOrderStatus | null>(null);
  const [issueReason, setIssueReason] = useState<OrderIssueReason>("fulfillment_details");
  const [search, setSearch] = useState("");
  const [queue, setQueue] = useState<"all" | AdminOrderQueue>("needs_approval");
  const [fulfillmentMethod, setFulfillmentMethod] = useState<"all" | AdminFulfillmentMethod>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | AdminOrderStatus>("all");
  const [locationId, setLocationId] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const issueReasonRef = useRef<HTMLSelectElement>(null);

  const canManageControls = session?.user.role === "owner" || session?.user.role === "manager";
  const canRunSensitiveTransitions = session?.user.role !== "kitchen";
  const selectedControls = controls.find((entry) => entry.id === selectedControlsId) ?? null;

  const deskPath = useMemo(() => {
    const params = new URLSearchParams();
    if (search.trim()) params.set("query", search.trim());
    if (queue !== "all") params.set("queue", queue);
    if (fulfillmentMethod !== "all") params.set("fulfillment_method", fulfillmentMethod);
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (locationId !== "all") params.set("location_id", locationId);
    if (startDate) params.set("starts_at", `${startDate}T00:00:00Z`);
    if (endDate) {
      const nextDay = new Date(`${endDate}T00:00:00Z`);
      nextDay.setUTCDate(nextDay.getUTCDate() + 1);
      params.set("ends_at", nextDay.toISOString());
    }
    const queryString = params.toString();
    return `/api/v1/admin/orders${queryString ? `?${queryString}` : ""}`;
  }, [endDate, fulfillmentMethod, locationId, queue, search, startDate, statusFilter]);

  const loadDesk = useCallback(async () => {
    const nextDesk = await request<AdminOrderDesk>(deskPath);
    setDesk(nextDesk);
  }, [deskPath, request]);

  const loadDetail = useCallback(async (reference: string) => {
    setDetailLoading(true);
    try {
      const nextDetail = await request<AdminOrderDetail>(`/api/v1/admin/orders/${reference}`);
      setDetail(nextDetail);
    } finally {
      setDetailLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void loadDesk()
      .catch((reason) => {
        if (active) {
          setError(reason instanceof ApiError ? reason.message : "The order desk could not be opened.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [loadDesk]);

  useEffect(() => {
    if (!canManageControls) {
      setControls([]);
      return;
    }
    let active = true;
    void request<LocationOrderControls[]>("/api/v1/admin/orders/controls")
      .then((nextControls) => {
        if (!active) return;
        setControls(nextControls);
        setSelectedControlsId((current) => current || nextControls[0]?.id || "");
      })
      .catch((reason) => {
        if (active) setError(reason instanceof ApiError ? reason.message : "Kitchen controls could not be loaded.");
      });
    return () => { active = false; };
  }, [canManageControls, request]);

  useEffect(() => {
    if (selectedControls) {
      setControlsDraft(draftFromControls(selectedControls));
    }
  }, [selectedControls]);

  useEffect(() => {
    if (!selectedReference) {
      setDetail(null);
      return;
    }
    let active = true;
    setDetail(null);
    setError(null);
    void loadDetail(selectedReference).catch((reason) => {
      if (active) {
        setError(reason instanceof ApiError ? reason.message : "This order detail could not be opened.");
      }
    });
    return () => { active = false; };
  }, [loadDetail, selectedReference]);

  useEffect(() => {
    if (!pendingIssue) {
      return;
    }
    const priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPendingIssue(null);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    issueReasonRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      priorFocus?.focus();
    };
  }, [pendingIssue]);

  async function refreshSelectedOrder(reference: string) {
    await Promise.all([loadDesk(), loadDetail(reference)]);
  }

  async function runTransition(nextStatus: AdminOrderStatus, reason?: OrderIssueReason) {
    if (!detail) return;
    setSavingTransition(nextStatus);
    setError(null);
    setNotice(null);
    try {
      await request(`/api/v1/admin/orders/${detail.public_reference}/transitions`, {
        method: "POST",
        body: JSON.stringify({ status: nextStatus, ...(reason ? { reason } : {}) }),
      });
      await refreshSelectedOrder(detail.public_reference);
      setNotice(`${orderStatusLabel(nextStatus)} was recorded for ${detail.public_reference}.`);
      setPendingIssue(null);
    } catch (reasonValue) {
      setError(reasonValue instanceof ApiError ? reasonValue.message : "The order status could not be recorded.");
    } finally {
      setSavingTransition(null);
    }
  }

  async function saveControls() {
    if (!selectedControls || !controlsDraft) return;
    setSavingControls(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await request<LocationOrderControls>(
        `/api/v1/admin/orders/locations/${selectedControls.id}/controls`,
        {
          method: "PUT",
          body: JSON.stringify({
            ...controlsDraft,
            online_ordering_paused_until: controlsDraft.online_ordering_state === "timed_pause" && controlsDraft.online_ordering_paused_until
              ? new Date(controlsDraft.online_ordering_paused_until).toISOString()
              : null,
          }),
        },
      );
      setControls((allControls) => allControls.map((entry) => entry.id === updated.id ? updated : entry));
      setNotice(`${updated.name} controls were saved.`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Kitchen controls could not be saved.");
    } finally {
      setSavingControls(false);
    }
  }

  return (
    <div className="admin-order-desk">
      <header className="admin-page-heading admin-order-heading">
        <div><p className="admin-kicker">Daily order desk</p><h1>Keep every handoff visible.</h1><p>Work from the next safe order step, with customer details and kitchen context kept together.</p></div>
        <div className="admin-order-heading-meta"><PackageCheck aria-hidden="true" /><span>{desk ? `${desk.total} orders in this view` : "Opening the order queues…"}</span></div>
      </header>

      {error ? <p className="admin-form-error" role="alert"><CircleAlert aria-hidden="true" /> {error}</p> : null}
      {notice ? <p className="admin-form-notice" role="status"><CheckCircle2 aria-hidden="true" /> {notice}</p> : null}

      <section className="admin-order-queue-tabs" aria-label="Order queues">
        {queues.map((entry) => {
          const count = desk?.queue_counts.find((item) => item.queue === entry.value)?.count;
          return <button key={entry.value} className={queue === entry.value ? "active" : undefined} type="button" onClick={() => setQueue(entry.value)}><span>{entry.value === "archive" ? <Archive aria-hidden="true" /> : null}{entry.label}</span>{count !== undefined ? <strong>{count}</strong> : null}</button>;
        })}
      </section>

      <section className="admin-order-filter-bar" aria-label="Filter orders">
        <label className="admin-order-search"><Search aria-hidden="true" /><span className="sr-only">Search orders</span><input placeholder="Order reference, customer, or email" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label><span>Location</span><select value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="all">All locations</option>{desk?.locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label>
        <label><span>Fulfilment</span><select value={fulfillmentMethod} onChange={(event) => setFulfillmentMethod(event.target.value as "all" | AdminFulfillmentMethod)}><option value="all">Pickup and delivery</option><option value="pickup">Pickup</option><option value="delivery">Delivery</option></select></label>
        <label><span>Status</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | AdminOrderStatus)}><option value="all">Any status</option>{statuses.map((entry) => <option key={entry} value={entry}>{orderStatusLabel(entry)}</option>)}</select></label>
        <label><span>From</span><input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
        <label><span>To</span><input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
      </section>

      <section className="admin-order-desk-grid">
        <div className="admin-order-list-panel">
          <div className="admin-order-list-heading"><div><SlidersHorizontal aria-hidden="true" /><span>{queue === "archive" ? "Archived outcomes" : "Working queue"}</span></div><small>{loading ? "Loading…" : `${desk?.orders.length ?? 0} shown`}</small></div>
          {loading ? <div className="admin-order-loading"><LoaderCircle aria-hidden="true" /> Loading the order queue…</div> : null}
          {!loading && !desk?.orders.length ? <div className="admin-order-empty"><PackageCheck aria-hidden="true" /><h2>Nothing needs attention here.</h2><p>Use another queue or adjust a filter. New customer orders appear in Needs approval.</p></div> : null}
          <ol className="admin-order-list">{desk?.orders.map((order) => <li key={order.public_reference}><button className={selectedReference === order.public_reference ? "selected" : undefined} type="button" onClick={() => setSelectedReference(order.public_reference)}><div><span className={`admin-order-status ${statusClass(order.status)}`}>{orderStatusLabel(order.status)}</span><strong>{order.public_reference}</strong><small>{order.recipient_name} · {order.item_count} item{order.item_count === 1 ? "" : "s"}</small></div><div><span>{formatOrderDeskPrice(order.total_minor, order.currency_code)}</span><small>{order.scheduled_for ? formatOrderDeskMoment(order.scheduled_for) : formatOrderDeskMoment(order.created_at)}</small><ChevronRight aria-hidden="true" /></div></button></li>)}</ol>
        </div>

        <aside className="admin-order-detail-panel" aria-live="polite">
          {!selectedReference ? <div className="admin-order-detail-empty"><PackageCheck aria-hidden="true" /><h2>Select an order.</h2><p>Choose an order from the queue to see the customer, food, allergens, notes, and recorded handoffs.</p></div> : null}
          {selectedReference && detailLoading && !detail ? <div className="admin-order-detail-empty"><LoaderCircle aria-hidden="true" /><p>Opening order details…</p></div> : null}
          {detail ? <>
            <header className="admin-order-detail-header"><div><span className={`admin-order-status ${statusClass(detail.status)}`}>{orderStatusLabel(detail.status)}</span><h2>{detail.public_reference}</h2><p>{detail.fulfillment_method === "delivery" ? <Truck aria-hidden="true" /> : <MapPin aria-hidden="true" />}{detail.location_name} · {detail.fulfillment_method === "delivery" ? "Delivery" : "Pickup"}</p></div><Button aria-label="Close order detail" size="icon" variant="quiet" onClick={() => setSelectedReference(null)}><X aria-hidden="true" /></Button></header>
            <section className="admin-order-actions"><p>Next safe step</p><div>{detail.valid_next_statuses.filter((entry) => !sensitiveStatuses.has(entry) || canRunSensitiveTransitions).map((entry) => <Button key={entry} disabled={savingTransition !== null} loading={savingTransition === entry} size="compact" variant={issueStatuses.has(entry) ? "secondary" : "primary"} onClick={() => issueStatuses.has(entry) ? setPendingIssue(entry) : void runTransition(entry)}>{orderActionLabel(entry)}</Button>)}</div></section>
            <section className="admin-order-detail-section"><h3>Customer and handoff</h3><dl><div><dt>Customer</dt><dd>{detail.recipient_name}</dd></div><div><dt>Email</dt><dd><a href={`mailto:${detail.recipient_email}`}>{detail.recipient_email}</a></dd></div><div><dt>Phone</dt><dd><a href={`tel:${detail.recipient_phone.replaceAll(/[^+\d]/g, "")}`}>{detail.recipient_phone}</a></dd></div><div><dt>Timing</dt><dd>{detail.scheduled_for ? formatOrderDeskMoment(detail.scheduled_for) : "As soon as possible"}</dd></div>{detail.delivery_address ? <div><dt>Delivery address</dt><dd>{detail.delivery_address}</dd></div> : null}<div><dt>Kitchen instructions</dt><dd>{detail.fulfillment_instructions ?? (detail.fulfillment_method === "pickup" ? detail.pickup_instructions ?? "No extra instruction." : detail.delivery_area ?? "No extra instruction.")}</dd></div></dl></section>
            <section className="admin-order-detail-section"><h3>Food and care</h3><ul className="admin-order-lines">{detail.lines.map((line, index) => <li key={`${line.menu_item_name}-${index}`}><div><strong>{line.quantity} × {line.menu_item_name}</strong>{line.selected_options.length ? <span>{line.selected_options.join(", ")}</span> : null}{line.note ? <span>Kitchen note: {line.note}</span> : null}</div><div><small>Ingredients</small><p>{line.ingredients.join(", ") || "Not recorded"}</p>{line.allergens.length ? <p className="admin-order-allergens">Allergens: {line.allergens.map((allergen) => allergen.name).join(", ")}</p> : null}{line.dietary_tags.length ? <p>Tags: {line.dietary_tags.join(", ")}</p> : null}</div></li>)}</ul></section>
            <section className="admin-order-detail-section admin-order-timeline"><h3>Recorded timeline</h3><ol>{detail.status_events.map((event, index) => <li key={`${event.status}-${event.created_at}-${index}`}><span><CheckCircle2 aria-hidden="true" /></span><div><strong>{orderStatusLabel(event.status)}</strong><time dateTime={event.created_at}>{formatOrderDeskMoment(event.created_at)}</time><p>{event.note}</p><small>{event.actor_name ? `Recorded by ${event.actor_name}` : "Recorded at checkout"}</small></div></li>)}</ol></section>
          </> : null}
        </aside>
      </section>

      {canManageControls ? <section className="admin-order-controls"><header><div><p className="admin-kicker">Online ordering controls</p><h2>Set the kitchen’s real local-demo capacity.</h2><p>These settings change server-side cart and checkout eligibility, not just a label in this desk.</p></div><span className={selectedControls?.ordering_available ? "available" : "paused"}>{selectedControls?.ordering_available ? "Ordering on" : "Ordering paused"}</span></header>{controls.length ? <div className="admin-order-controls-form"><label>Kitchen location<select value={selectedControlsId} onChange={(event) => setSelectedControlsId(event.target.value)}>{controls.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}</select></label><label>Online ordering<select value={controlsDraft?.online_ordering_state ?? "on"} onChange={(event) => setControlsDraft((current) => current ? { ...current, online_ordering_state: event.target.value as OnlineOrderingState } : current)}><option value="on">On</option><option value="timed_pause">Timed pause</option><option value="off">Off</option></select></label>{controlsDraft?.online_ordering_state === "timed_pause" ? <label>Pause ends<input required type="datetime-local" value={controlsDraft.online_ordering_paused_until} onChange={(event) => setControlsDraft((current) => current ? { ...current, online_ordering_paused_until: event.target.value } : current)} /></label> : null}<label>Preparation minutes<input min="0" max="240" type="number" value={controlsDraft?.preparation_minutes ?? 0} onChange={(event) => setControlsDraft((current) => current ? { ...current, preparation_minutes: Number(event.target.value) } : current)} /></label><label>Demo capacity<input min="0" max="10000" type="number" value={controlsDraft?.demo_capacity ?? 0} onChange={(event) => setControlsDraft((current) => current ? { ...current, demo_capacity: Number(event.target.value) } : current)} /></label><div className="admin-order-controls-save"><p>{selectedControls?.ordering_message}</p><Button loading={savingControls} onClick={() => void saveControls()}>Save kitchen controls</Button></div></div> : null}</section> : null}

      {pendingIssue ? <div className="admin-order-modal-backdrop" role="presentation"><section aria-labelledby="issue-transition-title" className="admin-order-modal" role="dialog" aria-modal="true"><button aria-label="Close confirmation" className="admin-order-modal-close" type="button" onClick={() => setPendingIssue(null)}><X aria-hidden="true" /></button><p className="admin-kicker">{sensitiveStatuses.has(pendingIssue) ? "Sensitive order outcome" : "Customer follow-up"}</p><h2 id="issue-transition-title">{orderActionLabel(pendingIssue)}</h2><p>{sensitiveStatuses.has(pendingIssue) ? "Confirm this outcome and choose the customer-safe reason that will appear in their tracker." : "Choose the customer-safe reason the tracker should show before the kitchen continues."}</p><label>Reason<select ref={issueReasonRef} value={issueReason} onChange={(event) => setIssueReason(event.target.value as OrderIssueReason)}>{issueReasons.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><div><Button variant="secondary" onClick={() => setPendingIssue(null)}>Go back</Button><Button loading={savingTransition === pendingIssue} variant={sensitiveStatuses.has(pendingIssue) ? "danger" : "primary"} onClick={() => void runTransition(pendingIssue, issueReason)}>Confirm {orderStatusLabel(pendingIssue)}</Button></div></section></div> : null}
    </div>
  );
}
