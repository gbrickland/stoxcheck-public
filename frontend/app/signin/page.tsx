"use client";

import { signInWithEmailAndPassword, signOut } from "firebase/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import SiteFooter from "../../components/SiteFooter";
import { auth, isFirebaseConfigured } from "../../lib/firebase";

const accountDomain = "accounts.stoxcheck.invalid";

export default function SignInPage() {
  const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const router = useRouter();

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError("");
    if (!auth) return setError("Firebase Authentication has not been configured for this deployment.");
    setBusy(true);
    try {
      const normalised = username.trim().toLowerCase();
      if (!/^member-[a-z0-9]{12}$/.test(normalised)) throw new Error("The username or password is incorrect.");
      const credential = await signInWithEmailAndPassword(auth, `${normalised}@${accountDomain}`, password);
      const token = await credential.user.getIdTokenResult(true);
      if (token.claims.stoxcheck_access !== true) {
        await signOut(auth);
        throw new Error("This account is not approved for Stoxcheck.");
      }
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(next?.startsWith("/") ? next : "/");
    } catch (problem) {
      const message = problem instanceof Error && !problem.message.includes("Firebase")
        ? problem.message : "The username or password is incorrect.";
      setError(message);
    } finally { setBusy(false); }
  };

  return <main className="auth-shell">
    <Link className="brand auth-brand" href="/">stoxcheck<span>.</span></Link>
    <section className="auth-card">
      <div className="auth-copy"><p className="eyebrow">Sign in to Stoxcheck</p><h1>Your stock-news<br/>sentiment dashboard.</h1>
        <p>Use the username and password you were given. There are ten project accounts, with sign-in handled securely by Firebase.</p></div>
      <form onSubmit={submit}>
        <h2>Sign in</h2>
        <label>Username<input type="text" autoComplete="username" required placeholder="member-••••••••••••" value={username} onChange={(e) => setUsername(e.target.value)}/></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)}/></label>
        {error && <p className="form-message error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy || !isFirebaseConfigured}>{busy ? "Please wait…" : "Sign in"}</button>
        <small>Need an account? Ask the Stoxcheck project administrator. Each time you sign in, you will be asked to accept the current <Link href="/terms">Terms</Link>, <Link href="/privacy">Privacy Notice</Link> and <Link href="/disclaimer">Financial Disclaimer</Link>.</small>
      </form>
    </section>
    <SiteFooter/>
  </main>;
}
