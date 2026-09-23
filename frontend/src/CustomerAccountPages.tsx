import { Heart, LogOut, MapPin, RotateCcw, UserRound } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Button } from "./components/ui/Button";
import {
  type CustomerAccountOrder,
  type CustomerAccountUser,
  type CustomerAddress,
  type CustomerFavorite,
  type CustomerReorder,
  useCustomerAccount,
} from "./customerAccount";
import { useCustomerCart } from "./customerCart";
import { customerMediaUrl, formatCustomerPrice } from "./customerCatalog";
import { CustomerSiteFooter, CustomerSiteHeader } from "./CustomerMenuPage";

type AccountDestination = { pathname?: unknown; search?: unknown };

function safeDestination(value: unknown): string {
  const candidate = value as AccountDestination | null;
  if (
    typeof candidate?.pathname === "string"
    && candidate.pathname.startsWith("/")
    && !candidate.pathname.startsWith("//")
  ) {
    return candidate.pathname + (typeof candidate.search === "string" ? candidate.search : "");
  }
  return "/account";
}

function formatAccountDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function CustomerAccountGuard() {
  const location = useLocation();
  const { ready, session } = useCustomerAccount();
  if (!ready) {
    return <main className="customer-account-loading">Checking your customer session…</main>;
  }
  return session ? <Outlet /> : <Navigate replace state={{ from: location }} to="/account/sign-in" />;
}

function CustomerAuthPage({ mode }: { mode: "sign-in" | "sign-up" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { ready, session, signIn, signUp } = useCustomerAccount();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const destination = safeDestination((location.state as { from?: AccountDestination } | null)?.from);
  const isSignUp = mode === "sign-up";

  if (ready && session) {
    return <Navigate replace to={destination} />;
  }

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      if (isSignUp) {
        await signUp(displayName, email, password);
      } else {
        await signIn(email, password);
      }
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Your account could not be opened.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-shell customer-account-page">
      <CustomerSiteHeader />
      <main className="customer-auth-layout">
        <section className="customer-auth-intro">
          <p className="eyebrow">Nosh account</p>
          <h1>{isSignUp ? "Make returning easy." : "Welcome back."}</h1>
          <p>{isSignUp ? "Save delivery details, keep a short list of favorites, and bring a past order back to the cart only after the kitchen checks it again." : "Sign in to see your saved details and current kitchen-checked order history."}</p>
        </section>
        <form className="customer-auth-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <header><UserRound aria-hidden="true" /><h2>{isSignUp ? "Create account" : "Customer sign in"}</h2></header>
          {isSignUp ? <label>First and last name<input autoComplete="name" required maxLength={120} minLength={2} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label> : null}
          <label>Email<input autoComplete="email" required maxLength={320} type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input autoComplete={isSignUp ? "new-password" : "current-password"} required minLength={isSignUp ? 12 : 8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {isSignUp ? <small>Use at least 12 characters. This local demo does not send email or collect payment credentials.</small> : null}
          {error ? <p className="customer-account-error" role="alert">{error}</p> : null}
          <Button loading={submitting} type="submit">{isSignUp ? "Create local account" : "Sign in"}</Button>
          <p>{isSignUp ? "Already have an account?" : "New to Nosh?"} <Link state={location.state} to={isSignUp ? "/account/sign-in" : "/account/sign-up"}>{isSignUp ? "Sign in" : "Create an account"}</Link></p>
        </form>
      </main>
      <CustomerSiteFooter />
    </div>
  );
}

export function CustomerAccountSignInPage() {
  return <CustomerAuthPage mode="sign-in" />;
}

export function CustomerAccountSignUpPage() {
  return <CustomerAuthPage mode="sign-up" />;
}

type AddressForm = {
  label: string;
  recipient_name: string;
  phone: string;
  address_text: string;
  is_default: boolean;
};

const blankAddress: AddressForm = {
  label: "Home",
  recipient_name: "",
  phone: "",
  address_text: "",
  is_default: false,
};

function AccountSection({ children, title, eyebrow }: { children: ReactNode; title: string; eyebrow: string }) {
  return <section className="customer-account-section"><header><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></header>{children}</section>;
}

export function CustomerAccountPage() {
  const { request, session, signOut, updateUser } = useCustomerAccount();
  const { replaceLines } = useCustomerCart();
  const navigate = useNavigate();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [favorites, setFavorites] = useState<CustomerFavorite[]>([]);
  const [orders, setOrders] = useState<CustomerAccountOrder[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [profileName, setProfileName] = useState(session?.user.display_name ?? "");
  const [profileEmail, setProfileEmail] = useState(session?.user.email ?? "");
  const [addressForm, setAddressForm] = useState<AddressForm>({
    ...blankAddress,
    recipient_name: session?.user.display_name ?? "",
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingAddress, setSavingAddress] = useState(false);
  const [reorderingReference, setReorderingReference] = useState<string | null>(null);

  const loadAccount = useMemo(() => async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [nextAddresses, nextFavorites, nextOrders] = await Promise.all([
        request<CustomerAddress[]>("/api/v1/account/addresses"),
        request<CustomerFavorite[]>("/api/v1/account/favorites"),
        request<CustomerAccountOrder[]>("/api/v1/account/orders"),
      ]);
      setAddresses(nextAddresses);
      setFavorites(nextFavorites);
      setOrders(nextOrders);
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "Your account could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  }, [request]);

  useEffect(() => { void loadAccount(); }, [loadAccount]);

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      const user = await request<CustomerAccountUser>("/api/v1/account/profile", {
        method: "PATCH",
        body: JSON.stringify({ display_name: profileName, email: profileEmail }),
      });
      updateUser(user);
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "Your profile could not be saved.");
    } finally {
      setSavingProfile(false);
    }
  };

  const saveAddress = async () => {
    setSavingAddress(true);
    try {
      const created = await request<CustomerAddress>("/api/v1/account/addresses", {
        method: "POST",
        body: JSON.stringify({ ...addressForm, is_default: addressForm.is_default || !addresses.length }),
      });
      setAddresses((current) => [created, ...current.map((address) => ({ ...address, is_default: false }))]);
      setAddressForm({ ...blankAddress, recipient_name: session?.user.display_name ?? "" });
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "This address could not be saved.");
    } finally {
      setSavingAddress(false);
    }
  };

  const makeDefault = async (address: CustomerAddress) => {
    try {
      const updated = await request<CustomerAddress>(`/api/v1/account/addresses/${address.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_default: true }),
      });
      setAddresses((current) => [updated, ...current.filter((entry) => entry.id !== updated.id).map((entry) => ({ ...entry, is_default: false }))]);
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "The default address could not be changed.");
    }
  };

  const deleteAddress = async (address: CustomerAddress) => {
    try {
      await request<void>(`/api/v1/account/addresses/${address.id}`, { method: "DELETE" });
      setAddresses((current) => current.filter((entry) => entry.id !== address.id));
      await loadAccount();
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "This address could not be removed.");
    }
  };

  const removeFavorite = async (favorite: CustomerFavorite) => {
    try {
      await request<void>(`/api/v1/account/favorites/${favorite.slug}`, { method: "DELETE" });
      setFavorites((current) => current.filter((entry) => entry.id !== favorite.id));
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "This favorite could not be removed.");
    }
  };

  const reorder = async (reference: string) => {
    setReorderingReference(reference);
    try {
      const result = await request<CustomerReorder>(`/api/v1/account/orders/${reference}/reorder`, { method: "POST" });
      await replaceLines(result.lines, result.location_slug);
      navigate(`/checkout?location=${encodeURIComponent(result.location_slug)}`);
    } catch (requestError) {
      setLoadError(requestError instanceof Error ? requestError.message : "The kitchen could not rebuild this order.");
    } finally {
      setReorderingReference(null);
    }
  };

  return (
    <div className="app-shell customer-account-page">
      <CustomerSiteHeader />
      <main className="customer-account-main">
        <header className="customer-account-hero"><p className="eyebrow">Customer account</p><h1>A useful place to return to.</h1><p>Your saved details stay private to this account. Past orders become a fresh, editable cart only after the current kitchen validates them.</p><Button size="compact" variant="secondary" onClick={signOut}><LogOut aria-hidden="true" /> Sign out</Button></header>
        {loadError ? <div className="customer-account-error customer-account-load-error" role="alert">{loadError} <Button size="compact" variant="quiet" onClick={() => void loadAccount()}>Try again</Button></div> : null}
        {isLoading ? <p className="customer-account-loading">Loading your saved account details…</p> : <div className="customer-account-grid">
          <div className="customer-account-primary">
            <AccountSection eyebrow="Profile" title="Your local details">
              <div className="customer-profile-form"><label>Name<input maxLength={120} minLength={2} value={profileName} onChange={(event) => setProfileName(event.target.value)} /></label><label>Email<input maxLength={320} type="email" value={profileEmail} onChange={(event) => setProfileEmail(event.target.value)} /></label><Button loading={savingProfile} onClick={() => void saveProfile()}>Save profile</Button></div>
            </AccountSection>
            <AccountSection eyebrow="Saved places" title="Addresses the kitchen can use">
              <div className="customer-address-list">{addresses.map((address) => <article key={address.id} className={address.is_default ? "customer-address-card default" : "customer-address-card"}><div><strong>{address.label}</strong>{address.is_default ? <span>Default</span> : null}<p>{address.recipient_name} · {address.phone}</p><p>{address.address_text}</p></div><footer>{!address.is_default ? <Button size="compact" variant="secondary" onClick={() => void makeDefault(address)}>Make default</Button> : null}<Button aria-label={`Remove ${address.label} address`} size="compact" variant="quiet" onClick={() => void deleteAddress(address)}>Remove</Button></footer></article>)}</div>
              <form className="customer-address-form" onSubmit={(event) => { event.preventDefault(); void saveAddress(); }}><h3>Add another address</h3><div><label>Label<input required maxLength={80} value={addressForm.label} onChange={(event) => setAddressForm((current) => ({ ...current, label: event.target.value }))} /></label><label>Phone<input required inputMode="tel" maxLength={30} minLength={7} value={addressForm.phone} onChange={(event) => setAddressForm((current) => ({ ...current, phone: event.target.value }))} /></label></div><label>Name for this address<input required maxLength={120} minLength={2} value={addressForm.recipient_name} onChange={(event) => setAddressForm((current) => ({ ...current, recipient_name: event.target.value }))} /></label><label>Address<textarea required maxLength={500} minLength={4} value={addressForm.address_text} onChange={(event) => setAddressForm((current) => ({ ...current, address_text: event.target.value }))} /></label><label className="customer-address-default"><input checked={addressForm.is_default} type="checkbox" onChange={(event) => setAddressForm((current) => ({ ...current, is_default: event.target.checked }))} />Make this my default delivery address</label><Button loading={savingAddress} type="submit"><MapPin aria-hidden="true" /> Save address</Button></form>
            </AccountSection>
          </div>
          <div className="customer-account-secondary">
            <AccountSection eyebrow="Favorites" title="Dishes worth keeping close"><div className="customer-favorites-list">{favorites.length ? favorites.map((favorite) => <article key={favorite.id}><Link to={`/menu/${favorite.slug}`}>{favorite.media ? <img alt={favorite.media.alt_text} src={customerMediaUrl(favorite.media) ?? undefined} /> : <Heart aria-hidden="true" />}<span><strong>{favorite.name}</strong><small>{formatCustomerPrice(favorite.final_price_minor, favorite.currency_code)}{favorite.is_available ? " · Available now" : " · Not currently available"}</small></span></Link><Button aria-label={`Remove ${favorite.name} from favorites`} size="compact" variant="quiet" onClick={() => void removeFavorite(favorite)}>Remove</Button></article>) : <p className="customer-account-empty">Save a dish from its detail page to find it here.</p>}</div></AccountSection>
            <AccountSection eyebrow="Order history" title="Bring an order back to edit"><div className="customer-history-list">{orders.length ? orders.map((order) => <article key={order.public_reference}><header><span>{order.status.replaceAll("_", " ")}</span><time dateTime={order.created_at}>{formatAccountDate(order.created_at)}</time></header><h3>{order.lines.map((line) => `${line.quantity} × ${line.menu_item_name}`).join(", ")}</h3><p>{order.location_name} · {order.fulfillment_method}</p><strong>{formatCustomerPrice(order.total_minor, order.currency_code)}</strong><footer><Link to={`/orders/${order.public_reference}`}>Receipt</Link><Button loading={reorderingReference === order.public_reference} size="compact" onClick={() => void reorder(order.public_reference)}><RotateCcw aria-hidden="true" /> Reorder</Button></footer></article>) : <p className="customer-account-empty">Completed account orders will appear here after checkout.</p>}</div></AccountSection>
          </div>
        </div>}
      </main>
      <CustomerSiteFooter />
    </div>
  );
}
