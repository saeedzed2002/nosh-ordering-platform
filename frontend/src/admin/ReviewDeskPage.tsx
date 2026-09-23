import { Check, EyeOff, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "../components/ui/Button";
import { ApiError } from "./api";
import { useAdminSession } from "./session";

type ReviewStatus = "pending" | "approved" | "rejected" | "hidden";
type ModerationAction = "approve" | "reject" | "hide" | "restore";
type AdminReview = {
  id: string;
  customer_name: string;
  customer_email: string;
  menu_item_name: string;
  rating: number;
  body: string;
  status: ReviewStatus;
  internal_reason: string | null;
  created_at: string;
};
type PendingModeration = { review: AdminReview; action: ModerationAction };

function actionLabel(action: ModerationAction): string {
  return { approve: "Approve", reject: "Reject", hide: "Hide", restore: "Restore" }[action];
}

export function ReviewDeskPage() {
  const { request } = useAdminSession();
  const [reviews, setReviews] = useState<AdminReview[]>([]);
  const [status, setStatus] = useState<ReviewStatus | "all">("pending");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingModeration | null>(null);
  const [internalReason, setInternalReason] = useState("");

  const load = useCallback(async () => {
    setError(null);
    const suffix = status === "all" ? "" : `?status=${status}`;
    setReviews(await request<AdminReview[]>(`/api/v1/admin/reviews${suffix}`));
  }, [request, status]);

  useEffect(() => {
    void load().catch((reason) => {
      setError(reason instanceof ApiError ? reason.message : "Reviews could not be loaded.");
    });
  }, [load]);

  const openModeration = (review: AdminReview, action: ModerationAction) => {
    setInternalReason("");
    setPending({ review, action });
  };

  const confirmModeration = async () => {
    if (!pending) return;
    const reasonRequired = pending.action === "reject" || pending.action === "hide";
    if (reasonRequired && !internalReason.trim()) {
      setError("Write an internal reason before completing this moderation action.");
      return;
    }
    setBusyId(pending.review.id);
    setError(null);
    try {
      await request(`/api/v1/admin/reviews/${pending.review.id}/moderation`, {
        method: "POST",
        body: JSON.stringify({
          action: pending.action,
          internal_reason: reasonRequired ? internalReason.trim() : undefined,
        }),
      });
      setPending(null);
      await load();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "This review could not be moderated.");
    } finally {
      setBusyId(null);
    }
  };

  return <section className="admin-review-desk"><header><div><p className="admin-kicker">Review moderation</p><h1>Publish feedback only when it is ready.</h1><p>Every entry came from a delivered order. Internal reasons stay private and are recorded in the owner audit history.</p></div><label>Status<select value={status} onChange={(event) => setStatus(event.target.value as ReviewStatus | "all")}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="hidden">Hidden</option><option value="all">All</option></select></label></header>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}<div className="admin-review-list">{reviews.length ? reviews.map((review) => <article key={review.id}><header><span>{review.status}</span><time dateTime={review.created_at}>{new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(review.created_at))}</time></header><h2>{review.menu_item_name} · {"★".repeat(review.rating)}</h2><p>{review.body}</p><footer><div><strong>{review.customer_name}</strong><small>{review.customer_email}</small>{review.internal_reason ? <small>Internal: {review.internal_reason}</small> : null}</div><div>{review.status !== "approved" ? <Button disabled={busyId === review.id} size="compact" onClick={() => openModeration(review, review.status === "hidden" ? "restore" : "approve")}><Check aria-hidden="true" /> {review.status === "hidden" ? "Restore" : "Approve"}</Button> : null}{review.status !== "rejected" ? <Button disabled={busyId === review.id} size="compact" variant="secondary" onClick={() => openModeration(review, "reject")}><X aria-hidden="true" /> Reject</Button> : null}{review.status === "approved" ? <Button disabled={busyId === review.id} size="compact" variant="secondary" onClick={() => openModeration(review, "hide")}><EyeOff aria-hidden="true" /> Hide</Button> : null}</div></footer></article>) : <p className="admin-empty-state">No reviews match this queue.</p>}</div>{pending ? <div className="admin-order-modal-backdrop" role="presentation"><section aria-labelledby="review-moderation-title" className="admin-order-modal" role="dialog" aria-modal="true"><button aria-label="Close moderation confirmation" className="admin-order-modal-close" type="button" onClick={() => setPending(null)}><X aria-hidden="true" /></button><p className="admin-kicker">Review moderation</p><h2 id="review-moderation-title">{actionLabel(pending.action)} this review?</h2><p>{pending.action === "reject" || pending.action === "hide" ? "Write a private reason for the team. Customers will never see it." : "This action changes what customers can see and records a safe audit event."}</p>{pending.action === "reject" || pending.action === "hide" ? <label>Internal reason<textarea autoFocus maxLength={500} value={internalReason} onChange={(event) => setInternalReason(event.target.value)} /></label> : null}<div><Button variant="secondary" onClick={() => setPending(null)}>Go back</Button><Button loading={busyId === pending.review.id} variant={pending.action === "reject" || pending.action === "hide" ? "danger" : "primary"} onClick={() => void confirmModeration()}>Confirm {actionLabel(pending.action)}</Button></div></section></div> : null}</section>;
}
