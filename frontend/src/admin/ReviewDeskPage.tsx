import { Check, EyeOff, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "../components/ui/Button";
import { useAdminSession } from "./session";

type ReviewStatus = "pending" | "approved" | "rejected" | "hidden";
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

export function ReviewDeskPage() {
  const { request } = useAdminSession();
  const [reviews, setReviews] = useState<AdminReview[]>([]);
  const [status, setStatus] = useState<ReviewStatus | "all">("pending");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      setReviews(await request<AdminReview[]>(`/api/v1/admin/reviews${status === "all" ? "" : `?status=${status}`}`));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Reviews could not be loaded.");
    }
  };

  useEffect(() => { void load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const moderate = async (review: AdminReview, action: "approve" | "reject" | "hide" | "restore") => {
    const internalReason = action === "reject" || action === "hide" ? window.prompt("Internal moderation reason")?.trim() : undefined;
    if ((action === "reject" || action === "hide") && !internalReason) return;
    setBusyId(review.id);
    try {
      await request(`/api/v1/admin/reviews/${review.id}/moderation`, { method: "POST", body: JSON.stringify({ action, internal_reason: internalReason }) });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "This review could not be moderated.");
    } finally { setBusyId(null); }
  };

  return <section className="admin-review-desk"><header><div><p className="admin-kicker">Review moderation</p><h1>Publish feedback only when it is ready.</h1><p>Every entry came from a delivered order. Internal reasons never appear on the public dish page.</p></div><label>Status<select value={status} onChange={(event) => setStatus(event.target.value as ReviewStatus | "all")}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="hidden">Hidden</option><option value="all">All</option></select></label></header>{error ? <p className="admin-form-error" role="alert">{error}</p> : null}<div className="admin-review-list">{reviews.length ? reviews.map((review) => <article key={review.id}><header><span>{review.status}</span><time dateTime={review.created_at}>{new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(review.created_at))}</time></header><h2>{review.menu_item_name} · {"★".repeat(review.rating)}</h2><p>{review.body}</p><footer><div><strong>{review.customer_name}</strong><small>{review.customer_email}</small>{review.internal_reason ? <small>Internal: {review.internal_reason}</small> : null}</div><div>{review.status !== "approved" ? <Button disabled={busyId === review.id} size="compact" onClick={() => void moderate(review, review.status === "hidden" ? "restore" : "approve")}><Check aria-hidden="true" /> {review.status === "hidden" ? "Restore" : "Approve"}</Button> : null}{review.status !== "rejected" ? <Button disabled={busyId === review.id} size="compact" variant="secondary" onClick={() => void moderate(review, "reject")}><X aria-hidden="true" /> Reject</Button> : null}{review.status === "approved" ? <Button disabled={busyId === review.id} size="compact" variant="secondary" onClick={() => void moderate(review, "hide")}><EyeOff aria-hidden="true" /> Hide</Button> : null}</div></footer></article>) : <p className="admin-empty-state">No reviews match this queue.</p>}</div></section>;
}
