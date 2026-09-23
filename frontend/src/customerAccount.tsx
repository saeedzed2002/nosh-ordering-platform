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

import { ApiError, apiUrl, readJson, unauthenticatedJson } from "./admin/api";

export type CustomerAccountUser = {
  id: string;
  email: string;
  display_name: string;
  role: "customer";
};

export type CustomerAddress = {
  id: string;
  label: string;
  recipient_name: string;
  phone: string;
  address_text: string;
  is_default: boolean;
};

export type CustomerFavorite = {
  id: string;
  slug: string;
  name: string;
  description: string;
  final_price_minor: number;
  currency_code: string;
  media: { id: string; alt_text: string; width: number; height: number } | null;
  is_available: boolean;
};

export type CustomerAccountOrder = {
  public_reference: string;
  created_at: string;
  status: string;
  fulfillment_method: "pickup" | "delivery";
  location_name: string;
  currency_code: string;
  total_minor: number;
  lines: Array<{
    menu_item_slug: string;
    menu_item_name: string;
    quantity: number;
    selected_option_names: string[];
  }>;
};

export type CustomerReorder = {
  location_slug: string;
  lines: Array<{
    client_line_id: string;
    menu_item_slug: string;
    quantity: number;
    option_ids: string[];
    note: string | null;
  }>;
  quote: {
    lines: Array<{
      client_line_id: string;
      unit_price_minor: number;
      line_total_minor: number;
    }>;
    subtotal_minor: number;
    currency_code: string;
  };
};

type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

type CustomerSession = TokenPair & { user: CustomerAccountUser };

type CustomerAccountContextValue = {
  ready: boolean;
  session: CustomerSession | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (displayName: string, email: string, password: string) => Promise<void>;
  signOut: () => void;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
  updateUser: (user: CustomerAccountUser) => void;
};

const storageKey = "nosh.customer.session.v1";
const CustomerAccountContext = createContext<CustomerAccountContextValue | null>(null);

function readStoredSession(): CustomerSession | null {
  try {
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) {
      return null;
    }
    const session = JSON.parse(stored) as CustomerSession;
    return session.user?.role === "customer" ? session : null;
  } catch {
    return null;
  }
}

function persistSession(session: CustomerSession | null) {
  if (session) {
    window.localStorage.setItem(storageKey, JSON.stringify(session));
  } else {
    window.localStorage.removeItem(storageKey);
  }
}

function authorizedHeaders(headers: HeadersInit | undefined, accessToken: string): Headers {
  const result = new Headers(headers);
  result.set("Authorization", `Bearer ${accessToken}`);
  return result;
}

export function CustomerAccountProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<CustomerSession | null>(null);
  const [ready, setReady] = useState(false);

  const replaceSession = useCallback((nextSession: CustomerSession | null) => {
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
      .then(readJson<CustomerAccountUser>)
      .then((user) => {
        if (user.role !== "customer") {
          throw new Error("The saved session is not a customer account.");
        }
        replaceSession({ ...storedSession, user });
      })
      .catch(() => replaceSession(null))
      .finally(() => setReady(true));
  }, [replaceSession]);

  const signOut = useCallback(() => replaceSession(null), [replaceSession]);

  const signIn = useCallback(async (email: string, password: string) => {
    const tokens = await unauthenticatedJson<TokenPair>("/api/v1/auth/customer/sign-in", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const user = await readJson<CustomerAccountUser>(await fetch(apiUrl("/api/v1/auth/me"), {
      headers: authorizedHeaders(undefined, tokens.access_token),
    }));
    if (user.role !== "customer") {
      throw new Error("This sign-in is not a customer account.");
    }
    replaceSession({ ...tokens, user });
  }, [replaceSession]);

  const signUp = useCallback(async (displayName: string, email: string, password: string) => {
    const tokens = await unauthenticatedJson<TokenPair>("/api/v1/auth/customer/sign-up", {
      method: "POST",
      body: JSON.stringify({ display_name: displayName, email, password }),
    });
    const user = await readJson<CustomerAccountUser>(await fetch(apiUrl("/api/v1/auth/me"), {
      headers: authorizedHeaders(undefined, tokens.access_token),
    }));
    replaceSession({ ...tokens, user });
  }, [replaceSession]);

  const refreshSession = useCallback(async (): Promise<CustomerSession | null> => {
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

  const fetchWithSession = useCallback(async (path: string, init: RequestInit = {}) => {
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
    const response = await makeRequest(session.access_token);
    if (response.status !== 401) {
      return response;
    }
    const nextSession = await refreshSession();
    return nextSession ? makeRequest(nextSession.access_token) : response;
  }, [refreshSession, session]);

  const request = useCallback(async <T,>(path: string, init: RequestInit = {}) => (
    readJson<T>(await fetchWithSession(path, init))
  ), [fetchWithSession]);

  const updateUser = useCallback((user: CustomerAccountUser) => {
    if (session) {
      replaceSession({ ...session, user });
    }
  }, [replaceSession, session]);

  const value = useMemo<CustomerAccountContextValue>(() => ({
    ready,
    session,
    signIn,
    signOut,
    signUp,
    request,
    updateUser,
  }), [ready, request, session, signIn, signOut, signUp, updateUser]);

  return <CustomerAccountContext.Provider value={value}>{children}</CustomerAccountContext.Provider>;
}

export function useCustomerAccount(): CustomerAccountContextValue {
  const context = useContext(CustomerAccountContext);
  if (!context) {
    throw new Error("Customer account components must be rendered within CustomerAccountProvider.");
  }
  return context;
}
