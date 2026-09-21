import {
  Eye,
  FileText,
  ImagePlus,
  LoaderCircle,
  RotateCcw,
  Save,
  Send,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/Field";
import { ApiError } from "./api";
import { ProtectedMediaImage } from "./ProtectedMediaImage";
import { useAdminSession } from "./session";

type MediaSummary = {
  id: string;
  alt_text: string;
  width: number;
  height: number;
};

type HomeDraft = {
  heading: string;
  supporting_copy: string;
  action_label: string | null;
  action_href: string | null;
  media_id: string | null;
};

type HomeRevision = {
  id: string;
  action: "draft_saved" | "published";
  actor_name: string;
  created_at: string;
  heading: string;
  media_id: string | null;
  snapshot: HomeDraft;
};

type HomeContent = HomeDraft & {
  id: string;
  content_key: string;
  display_order: number;
  publication_state: "draft" | "published";
  media: MediaSummary | null;
  latest_draft: HomeRevision | null;
  history: HomeRevision[];
};

type MediaAsset = {
  id: string;
  original_filename: string;
  alt_text: string;
  publication_state: "draft" | "published";
};

const blockLabels: Record<string, string> = {
  hero: "Hero welcome",
  "featured-dish": "Featured dish",
  "kitchen-story": "Kitchen story",
  "location-callout": "Location callout",
};

function formFromContent(content: HomeContent, preferDraft = true): HomeDraft {
  if (preferDraft && content.latest_draft) {
    return content.latest_draft.snapshot;
  }

  return {
    heading: content.heading,
    supporting_copy: content.supporting_copy,
    action_label: content.action_label,
    action_href: content.action_href,
    media_id: content.media?.id ?? null,
  };
}

function draftsMatch(left: HomeDraft, right: HomeDraft): boolean {
  return (
    left.heading === right.heading &&
    left.supporting_copy === right.supporting_copy &&
    left.action_label === right.action_label &&
    left.action_href === right.action_href &&
    left.media_id === right.media_id
  );
}

function updateContent(
  allContent: HomeContent[],
  nextContent: HomeContent,
): HomeContent[] {
  return allContent.map((content) =>
    content.content_key === nextContent.content_key ? nextContent : content,
  );
}

function displayTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
  }).format(new Date(value));
}

export function HomeEditorPage() {
  const { request } = useAdminSession();
  const [content, setContent] = useState<HomeContent[]>([]);
  const [mediaAssets, setMediaAssets] = useState<MediaAsset[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<HomeDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void Promise.all([
      request<HomeContent[]>("/api/v1/admin/home"),
      request<MediaAsset[]>("/api/v1/admin/media"),
    ])
      .then(([nextContent, nextMedia]) => {
        if (!active) {
          return;
        }
        setContent(nextContent);
        setMediaAssets(nextMedia);
        const firstContent = nextContent[0];
        if (firstContent) {
          setSelectedKey(firstContent.content_key);
          setDraft(formFromContent(firstContent));
        }
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof ApiError
              ? reason.message
              : "The local publishing data is unavailable.",
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
  }, [request]);

  const selectedContent = useMemo(
    () => content.find((block) => block.content_key === selectedKey) ?? null,
    [content, selectedKey],
  );
  const baseline = selectedContent ? formFromContent(selectedContent) : null;
  const isDirty = Boolean(draft && baseline && !draftsMatch(draft, baseline));
  const selectedMedia = mediaAssets.find((asset) => asset.id === draft?.media_id) ?? null;

  useEffect(() => {
    if (!isDirty) {
      return undefined;
    }

    const warnBeforeExit = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeExit);
    return () => window.removeEventListener("beforeunload", warnBeforeExit);
  }, [isDirty]);

  function selectBlock(nextContent: HomeContent) {
    setSelectedKey(nextContent.content_key);
    setDraft(formFromContent(nextContent));
    setError(null);
    setNotice(null);
  }

  async function saveDraft() {
    if (!selectedContent || !draft) {
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const savedContent = await request<HomeContent>(
        `/api/v1/admin/home/${selectedContent.content_key}/draft`,
        { method: "PUT", body: JSON.stringify(draft) },
      );
      setContent((allContent) => updateContent(allContent, savedContent));
      setDraft(formFromContent(savedContent));
      setNotice("Private draft saved. It is not on the customer page yet.");
    } catch (reason) {
      setError(
        reason instanceof ApiError ? reason.message : "The draft could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function publishDraft() {
    if (!selectedContent || !draft) {
      return;
    }
    if (isDirty || !selectedContent.latest_draft) {
      setError("Save this version first, then publish the saved draft.");
      return;
    }

    setPublishing(true);
    setError(null);
    setNotice(null);
    try {
      const publishedContent = await request<HomeContent>(
        `/api/v1/admin/home/${selectedContent.content_key}/publish`,
        {
          method: "POST",
          body: JSON.stringify({ revision_id: selectedContent.latest_draft.id }),
        },
      );
      setContent((allContent) => updateContent(allContent, publishedContent));
      setDraft(formFromContent(publishedContent, false));
      setNotice("Published. Refresh the customer home page to see the live content.");
    } catch (reason) {
      setError(
        reason instanceof ApiError ? reason.message : "The draft could not be published.",
      );
    } finally {
      setPublishing(false);
    }
  }

  if (loading) {
    return <div className="admin-inline-loading"><LoaderCircle aria-hidden="true" /> Loading publishing desk…</div>;
  }

  if (!selectedContent || !draft) {
    return <div className="admin-empty-state">No editable home sections are available.</div>;
  }

  return (
    <div className="admin-home-editor">
      <header className="admin-page-heading admin-home-heading">
        <div>
          <p className="admin-kicker">Home page</p>
          <h1>Set the tone before service starts.</h1>
          <p>Choose a section, make the change, then use the live preview to decide.</p>
        </div>
        <div className={`admin-draft-status ${isDirty ? "dirty" : ""}`}>
          <FileText aria-hidden="true" />
          <span>{isDirty ? "Unsaved changes" : "Saved version selected"}</span>
        </div>
      </header>

      <div className="admin-home-grid">
        <aside className="admin-section-rail" aria-label="Editable home page sections">
          <p>Page sections</p>
          {content.map((block) => (
            <button
              key={block.content_key}
              className={block.content_key === selectedContent.content_key ? "active" : undefined}
              type="button"
              onClick={() => selectBlock(block)}
            >
              <span>{String(block.display_order + 1).padStart(2, "0")}</span>
              <strong>{blockLabels[block.content_key] ?? block.content_key}</strong>
              <small>{block.latest_draft ? "Draft ready" : "Live version"}</small>
            </button>
          ))}
        </aside>

        <section className="admin-editor-panel" aria-labelledby="home-editor-title">
          <div className="admin-panel-heading">
            <div>
              <p className="admin-kicker">Editing {blockLabels[selectedContent.content_key] ?? selectedContent.content_key}</p>
              <h2 id="home-editor-title">Write it as the customer should read it.</h2>
            </div>
            {selectedContent.latest_draft ? <span className="admin-draft-chip">Draft ready</span> : null}
          </div>
          <TextField
            label="Headline"
            maxLength={240}
            value={draft.heading}
            onChange={(event) => setDraft({ ...draft, heading: event.target.value })}
          />
          <div className="admin-textarea-field">
            <label htmlFor="home-supporting-copy">Supporting copy</label>
            <textarea
              id="home-supporting-copy"
              rows={5}
              value={draft.supporting_copy}
              onChange={(event) => setDraft({ ...draft, supporting_copy: event.target.value })}
            />
          </div>
          <div className="admin-form-two-column">
            <TextField
              label="Action label"
              maxLength={100}
              value={draft.action_label ?? ""}
              onChange={(event) =>
                setDraft({ ...draft, action_label: event.target.value || null })
              }
            />
            <TextField
              label="Action destination"
              hint="Use a local path or an on-page anchor."
              maxLength={255}
              value={draft.action_href ?? ""}
              onChange={(event) => setDraft({ ...draft, action_href: event.target.value || null })}
            />
          </div>
          <div className="admin-media-select">
            <div>
              <label htmlFor="home-media">Section image</label>
              <p>Choose an existing library image. Draft images remain private until publish.</p>
            </div>
            <select
              id="home-media"
              value={draft.media_id ?? ""}
              onChange={(event) => setDraft({ ...draft, media_id: event.target.value || null })}
            >
              <option value="">No image</option>
              {mediaAssets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.original_filename} · {asset.publication_state}
                </option>
              ))}
            </select>
            <a href="/admin/media"><ImagePlus aria-hidden="true" /> Add or refine an image</a>
          </div>
          {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
          {notice ? <p className="admin-form-notice" role="status">{notice}</p> : null}
          <div className="admin-editor-actions">
            <Button loading={saving} onClick={() => void saveDraft()}>
              <Save aria-hidden="true" /> Save draft
            </Button>
            <Button
              disabled={!isDirty}
              variant="quiet"
              onClick={() => {
                setDraft(formFromContent(selectedContent));
                setNotice("Restored the saved version.");
              }}
            >
              <RotateCcw aria-hidden="true" /> Restore saved
            </Button>
            <Button loading={publishing} variant="secondary" onClick={() => void publishDraft()}>
              <Send aria-hidden="true" /> Publish saved draft
            </Button>
          </div>
          {selectedContent.history.length > 0 ? (
            <div className="admin-history">
              <p>Recent changes</p>
              <ol>
                {selectedContent.history.map((revision) => (
                  <li key={revision.id}>
                    <span>{revision.action === "published" ? "Published" : "Draft saved"}</span>
                    <strong>{revision.heading}</strong>
                    <small>{revision.actor_name} · {displayTime(revision.created_at)}</small>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </section>

        <aside className="admin-preview-panel" aria-labelledby="home-preview-title">
          <div className="admin-preview-label"><Eye aria-hidden="true" /> Live preview</div>
          <div className="admin-home-preview">
            <div>
              <p><Sparkles aria-hidden="true" /> Nosh, today</p>
              <h2 id="home-preview-title">{draft.heading || "Your headline will appear here."}</h2>
              <span>{draft.supporting_copy || "Supporting copy will appear here."}</span>
              {draft.action_label ? <button type="button">{draft.action_label}</button> : null}
            </div>
            <ProtectedMediaImage
              alt={selectedMedia?.alt_text ?? "Selected home section"}
              className="admin-home-preview-image"
              mediaId={draft.media_id}
            />
          </div>
          <p className="admin-preview-note">
            This is the exact selected draft. Publishing changes the public content API; customer
            pages update on their next load.
          </p>
        </aside>
      </div>
    </div>
  );
}
