import { Check, FileImage, LoaderCircle, SlidersHorizontal, Upload, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/Field";
import { ApiError } from "./api";
import { ProtectedMediaImage } from "./ProtectedMediaImage";
import { useAdminSession } from "./session";

type MediaUsage = {
  content_key: string;
  label: string;
  state: string;
};

type MediaAsset = {
  id: string;
  original_filename: string;
  mime_type: string;
  byte_size: number;
  width: number;
  height: number;
  alt_text: string;
  focal_point_x: number;
  focal_point_y: number;
  source_description: string | null;
  credit: string | null;
  publication_state: "draft" | "published";
  usages: MediaUsage[];
};

type MediaDetails = Pick<
  MediaAsset,
  "alt_text" | "focal_point_x" | "focal_point_y" | "source_description" | "credit" | "publication_state"
>;

type SortOrder = "newest" | "oldest";

function detailsFromAsset(asset: MediaAsset): MediaDetails {
  return {
    alt_text: asset.alt_text,
    focal_point_x: asset.focal_point_x,
    focal_point_y: asset.focal_point_y,
    source_description: asset.source_description,
    credit: asset.credit,
    publication_state: asset.publication_state,
  };
}

function formatBytes(byteSize: number): string {
  return `${(byteSize / 1024).toFixed(byteSize > 1024 * 1024 ? 1 : 0)} KB`;
}

export function MediaLibraryPage() {
  const { request } = useAdminSession();
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [details, setDetails] = useState<MediaDetails | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>("newest");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadMedia = useCallback(async () => {
    const nextAssets = await request<MediaAsset[]>("/api/v1/admin/media");
    setAssets(nextAssets);
    setSelectedId((currentId) => currentId ?? nextAssets[0]?.id ?? null);
  }, [request]);

  useEffect(() => {
    let active = true;
    void loadMedia()
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof ApiError ? reason.message : "The media library is unavailable.",
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
  }, [loadMedia]);

  const selectedAsset = assets.find((asset) => asset.id === selectedId) ?? null;
  const sortedAssets = useMemo(
    () => (sortOrder === "newest" ? assets : [...assets].reverse()),
    [assets, sortOrder],
  );

  useEffect(() => {
    setDetails(selectedAsset ? detailsFromAsset(selectedAsset) : null);
  }, [selectedAsset]);

  function selectAsset(asset: MediaAsset) {
    setSelectedId(asset.id);
    setError(null);
    setNotice(null);
  }

  async function saveMetadata() {
    if (!selectedAsset || !details) {
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updatedAsset = await request<MediaAsset>(`/api/v1/admin/media/${selectedAsset.id}`, {
        method: "PATCH",
        body: JSON.stringify(details),
      });
      setAssets((allAssets) =>
        allAssets.map((asset) => (asset.id === updatedAsset.id ? updatedAsset : asset)),
      );
      setNotice("Image details and crop focus saved.");
    } catch (reason) {
      setError(
        reason instanceof ApiError ? reason.message : "Image details could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function uploadMedia(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const file = formData.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose an image file before uploading.");
      return;
    }

    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const createdAsset = await request<MediaAsset>("/api/v1/admin/media", {
        method: "POST",
        body: formData,
      });
      setAssets((allAssets) => [createdAsset, ...allAssets]);
      setSelectedId(createdAsset.id);
      setShowUpload(false);
      form.reset();
      setNotice("Image uploaded as a private draft. Choose it in Home when ready.");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "The image could not be uploaded.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return <div className="admin-inline-loading"><LoaderCircle aria-hidden="true" /> Loading media library…</div>;
  }

  return (
    <div className="admin-media-library">
      <header className="admin-page-heading admin-media-heading">
        <div>
          <p className="admin-kicker">Media library</p>
          <h1>Every image should earn its place.</h1>
          <p>Describe it clearly, set its focal crop, and see its live and draft uses.</p>
        </div>
        <Button onClick={() => setShowUpload((visible) => !visible)}>
          {showUpload ? <X aria-hidden="true" /> : <Upload aria-hidden="true" />}
          {showUpload ? "Close upload" : "Upload image"}
        </Button>
      </header>

      {showUpload ? (
        <section className="admin-upload-panel" aria-labelledby="upload-image-title">
          <div>
            <p className="admin-kicker">New library image</p>
            <h2 id="upload-image-title">Add it once, then use it with intention.</h2>
          </div>
          <form onSubmit={(event) => void uploadMedia(event)}>
            <TextField accept="image/jpeg,image/png,image/webp" label="Image file" name="file" type="file" required />
            <TextField label="Alt text" name="alt_text" hint="Describe the image for customers who cannot see it." maxLength={500} required />
            <div className="admin-form-two-column">
              <TextField defaultValue="50" label="Focus horizontal" max="100" min="0" name="focal_point_x" type="number" required />
              <TextField defaultValue="50" label="Focus vertical" max="100" min="0" name="focal_point_y" type="number" required />
            </div>
            <div className="admin-form-two-column">
              <TextField label="Source note" name="source_description" maxLength={500} />
              <TextField label="Credit" name="credit" maxLength={500} />
            </div>
            <Button loading={uploading} type="submit"><Upload aria-hidden="true" /> Upload private image</Button>
          </form>
        </section>
      ) : null}

      {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
      {notice ? <p className="admin-form-notice" role="status">{notice}</p> : null}

      <div className="admin-media-workspace">
        <section className="admin-media-grid-panel" aria-labelledby="media-grid-title">
          <div className="admin-media-grid-heading">
            <div>
              <p className="admin-kicker">Library</p>
              <h2 id="media-grid-title">{assets.length} available images</h2>
            </div>
            <label className="admin-sort-control">
              <SlidersHorizontal aria-hidden="true" />
              <span>Order</span>
              <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as SortOrder)}>
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
              </select>
            </label>
          </div>
          <div className="admin-media-grid">
            {sortedAssets.map((asset) => (
              <button
                key={asset.id}
                className={asset.id === selectedAsset?.id ? "selected" : undefined}
                type="button"
                onClick={() => selectAsset(asset)}
              >
                <ProtectedMediaImage
                  alt={asset.alt_text}
                  className="admin-media-grid-image"
                  mediaId={asset.id}
                  refreshKey={`${asset.focal_point_x}-${asset.focal_point_y}`}
                />
                <span>
                  <strong>{asset.original_filename}</strong>
                  <small>{asset.publication_state === "published" ? "Live-ready" : "Private draft"}</small>
                </span>
              </button>
            ))}
          </div>
        </section>

        {selectedAsset && details ? (
          <aside className="admin-media-detail" aria-labelledby="media-detail-title">
            <ProtectedMediaImage
              alt={details.alt_text}
              className="admin-media-detail-image"
              mediaId={selectedAsset.id}
              refreshKey={`${selectedAsset.focal_point_x}-${selectedAsset.focal_point_y}`}
            />
            <div className="admin-panel-heading">
              <div>
                <p className="admin-kicker">Image details</p>
                <h2 id="media-detail-title">{selectedAsset.original_filename}</h2>
              </div>
              <span className={`admin-state-chip ${details.publication_state}`}>{details.publication_state}</span>
            </div>
            <p className="admin-media-file-meta">
              {selectedAsset.width} × {selectedAsset.height} · {formatBytes(selectedAsset.byte_size)} · {selectedAsset.mime_type}
            </p>
            <TextField
              label="Alt text"
              maxLength={500}
              value={details.alt_text}
              onChange={(event) => setDetails({ ...details, alt_text: event.target.value })}
            />
            <div className="admin-focus-control">
              <div>
                <label htmlFor="focus-horizontal">Horizontal focal point</label>
                <span>{details.focal_point_x}%</span>
              </div>
              <input
                id="focus-horizontal"
                max="100"
                min="0"
                type="range"
                value={details.focal_point_x}
                onChange={(event) =>
                  setDetails({ ...details, focal_point_x: Number(event.target.value) })
                }
              />
              <div>
                <label htmlFor="focus-vertical">Vertical focal point</label>
                <span>{details.focal_point_y}%</span>
              </div>
              <input
                id="focus-vertical"
                max="100"
                min="0"
                type="range"
                value={details.focal_point_y}
                onChange={(event) =>
                  setDetails({ ...details, focal_point_y: Number(event.target.value) })
                }
              />
            </div>
            <div className="admin-form-two-column">
              <TextField
                label="Source note"
                maxLength={500}
                value={details.source_description ?? ""}
                onChange={(event) =>
                  setDetails({ ...details, source_description: event.target.value || null })
                }
              />
              <TextField
                label="Credit"
                maxLength={500}
                value={details.credit ?? ""}
                onChange={(event) => setDetails({ ...details, credit: event.target.value || null })}
              />
            </div>
            <label className="admin-state-select" htmlFor="media-state">
              <span>Visibility</span>
              <select
                id="media-state"
                value={details.publication_state}
                onChange={(event) =>
                  setDetails({
                    ...details,
                    publication_state: event.target.value as MediaDetails["publication_state"],
                  })
                }
              >
                <option value="draft">Private draft</option>
                <option value="published">Published library asset</option>
              </select>
            </label>
            <Button loading={saving} onClick={() => void saveMetadata()}>
              <Check aria-hidden="true" /> Save image details
            </Button>
            <div className="admin-media-uses">
              <p>Where this image is used</p>
              {selectedAsset.usages.length > 0 ? (
                <ul>
                  {selectedAsset.usages.map((usage, index) => (
                    <li key={`${usage.content_key}-${usage.state}-${index}`}>
                      <FileImage aria-hidden="true" />
                      <span>{usage.label}</span>
                      <small>{usage.state.replaceAll("_", " ")}</small>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="admin-media-unused">Not used on a home section yet. <Link to="/admin/home">Choose it in Home.</Link></p>
              )}
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
