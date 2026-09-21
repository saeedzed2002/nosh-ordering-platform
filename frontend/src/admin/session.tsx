/* eslint-disable react-refresh/only-export-components */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

import { ApiError, apiUrl, readJson, unauthenticatedJson } from "./api";

export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  role: "owner" | "manager" | "kitchen";
};

type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

type StoredSession = TokenPair & {
  user: AdminUser;
};

type AdminSessionContextValue = {
  ready: boolean;
  session: StoredSession | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
  fetchWithSession: (path: string, init?: RequestInit) => Promise<Response>;
};

const storageKey = "nosh.admin.session";
const AdminSessionContext = createContext<AdminSessionContextValue | null>(null);

function readStoredSession(): StoredSession | null {
  try {
    const rawSession = window.sessionStorage.getItem(storageKey);
    if (!rawSession) {
      return null;
    }

    return JSON.parse(rawSession) as StoredSession;
  } catch {
    return null;
  }
}

function persistSession(session: StoredSession | null): void {
  if (session) {
    window.sessionStorage.setItem(storageKey, JSON.stringify(session));
  } else {
    window.sessionStorage.removeItem(storageKey);
  }
}

function authorizedHeaders(headers: HeadersInit | undefined, accessToken: string): Headers {
  const result = new Headers(headers);
  result.set("Authorization", `Bearer ${accessToken}`);
  return result;
}

export function AdminSessionProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [ready, setReady] = useState(false);

  const replaceSession = useCallback((nextSession: StoredSession | null) => {
    persistSession(nextSession);
    setSession(nextSession);
  }, []);

  useEffect(() => {
    const storedSession = readStoredSession();
    if (!storedSession) {
      setReady(true);
      return;
    }

    void fetch(apiUrl("/api/v1/auth/me"), {
      headers: authorizedHeaders(undefined, storedSession.access_token),
    })
      .then(readJson<AdminUser>)
      .then((user) => replaceSession({ ...storedSession, user }))
      .catch(() => replaceSession(null))
      .finally(() => setReady(true));
  }, [replaceSession]);

  const signOut = useCallback(() => replaceSession(null), [replaceSession]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await unauthenticatedJson<TokenPair>("/api/v1/auth/admin/sign-in", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const user = await readJson<AdminUser>(
        await fetch(apiUrl("/api/v1/auth/me"), {
          headers: authorizedHeaders(undefined, tokens.access_token),
        }),
      );
      replaceSession({ ...tokens, user });
    },
    [replaceSession],
  );

  const refreshSession = useCallback(async (): Promise<StoredSession | null> => {
    if (!session) {
      return null;
    }

    try {
      const tokens = await unauthenticatedJson<TokenPair>("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: session.refresh_token }),
      });
      const nextSession = { ...session, ...tokens };
      replaceSession(nextSession);
      return nextSession;
    } catch {
      replaceSession(null);
      return null;
    }
  }, [replaceSession, session]);

  const fetchWithSession = useCallback(
    async (path: string, init: RequestInit = {}): Promise<Response> => {
      if (!session) {
        throw new ApiError(401, "Sign in to continue.");
      }

      const makeRequest = (accessToken: string) => {
        const headers = authorizedHeaders(init.headers, accessToken);
        if (init.body && !(init.body instanceof FormData)) {
          headers.set("Content-Type", "application/json");
        }
        return fetch(apiUrl(path), { ...init, headers });
      };

      let response = await makeRequest(session.access_token);
      if (response.status !== 401) {
        return response;
      }

      const refreshedSession = await refreshSession();
      if (!refreshedSession) {
        return response;
      }

      response = await makeRequest(refreshedSession.access_token);
      return response;
    },
    [refreshSession, session],
  );

  const request = useCallback(
    async <T,>(path: string, init: RequestInit = {}): Promise<T> =>
      readJson<T>(await fetchWithSession(path, init)),
    [fetchWithSession],
  );

  const value = useMemo<AdminSessionContextValue>(
    () => ({ ready, session, signIn, signOut, request, fetchWithSession }),
    [fetchWithSession, ready, request, session, signIn, signOut],
  );

  return <AdminSessionContext.Provider value={value}>{children}</AdminSessionContext.Provider>;
}

export function useAdminSession(): AdminSessionContextValue {
  const context = useContext(AdminSessionContext);
  if (!context) {
    throw new Error("useAdminSession must be used within AdminSessionProvider.");
  }
  return context;
}
