import { ArrowRight, KeyRound, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/Field";
import { ApiError } from "./api";
import { useAdminSession } from "./session";

export function AdminSignInPage() {
  const location = useLocation();
  const { ready, session, signIn } = useAdminSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!ready) {
    return <main className="admin-loading-page">Checking your local session…</main>;
  }

  if (session) {
    const requestedPath = location.state?.from?.pathname;
    return <Navigate to={typeof requestedPath === "string" ? requestedPath : "/admin/home"} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signIn(email, password);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "The local sign-in service is unavailable. Check the running backend.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="admin-sign-in-page">
      <section className="admin-sign-in-intro" aria-labelledby="admin-sign-in-title">
        <a className="admin-sign-in-wordmark" href="/">Nosh<span>.</span></a>
        <p className="eyebrow"><ShieldCheck aria-hidden="true" /> Local administration</p>
        <h1 id="admin-sign-in-title">A calm place to keep today’s service accurate.</h1>
        <p>
          Edit the kitchen home page, review images, and make the public change only when
          it is ready.
        </p>
        <div className="admin-sign-in-note">
          <KeyRound aria-hidden="true" />
          <span>Your session is stored only in this browser tab.</span>
        </div>
      </section>
      <section className="admin-sign-in-card" aria-labelledby="admin-sign-in-form-title">
        <p className="admin-kicker">Staff access</p>
        <h2 id="admin-sign-in-form-title">Sign in to the kitchen desk.</h2>
        <form onSubmit={handleSubmit}>
          <TextField
            autoComplete="email"
            label="Email address"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <TextField
            autoComplete="current-password"
            label="Password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
          <Button className="admin-form-submit" loading={isSubmitting} type="submit">
            Sign in <ArrowRight aria-hidden="true" />
          </Button>
        </form>
      </section>
    </main>
  );
}
