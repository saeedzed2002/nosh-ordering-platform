import { apiBaseUrl } from "../site";

type ApiProblem = {
  detail?: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getApiErrorMessage(payload: unknown, fallback: string): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof (payload as ApiProblem).detail === "string"
  ) {
    return (payload as ApiProblem).detail ?? fallback;
  }

  return fallback;
}

export async function readJson<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new ApiError(
      response.status,
      getApiErrorMessage(payload, "The local API could not complete that request."),
    );
  }

  return payload as T;
}

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}

export async function unauthenticatedJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  return readJson<T>(await fetch(apiUrl(path), { ...init, headers }));
}
