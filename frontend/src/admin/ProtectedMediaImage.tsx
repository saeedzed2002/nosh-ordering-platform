import { ImageOff } from "lucide-react";
import { useEffect, useState } from "react";

import { useAdminSession } from "./session";

type ProtectedMediaImageProps = {
  alt: string;
  className?: string;
  mediaId: string | null;
  refreshKey?: string | number;
};

export function ProtectedMediaImage({
  alt,
  className,
  mediaId,
  refreshKey,
}: ProtectedMediaImageProps) {
  const { fetchWithSession } = useAdminSession();
  const [source, setSource] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let active = true;

    if (!mediaId) {
      setSource(null);
      return undefined;
    }

    void fetchWithSession(`/api/v1/admin/media/${mediaId}/thumbnail`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("The image preview is unavailable.");
        }
        return response.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) {
          setSource(objectUrl);
        }
      })
      .catch(() => {
        if (active) {
          setSource(null);
        }
      });

    return () => {
      active = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [fetchWithSession, mediaId, refreshKey]);

  if (!source) {
    return (
      <div className={`${className ?? ""} admin-media-placeholder`} aria-label={alt}>
        <ImageOff aria-hidden="true" />
        <span>Image preview unavailable</span>
      </div>
    );
  }

  return <img className={className} src={source} alt={alt} />;
}
