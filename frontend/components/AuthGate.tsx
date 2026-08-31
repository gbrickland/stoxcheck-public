"use client";

/** Protect application pages while keeping legal and sign-in material publicly readable. */
import { onAuthStateChanged, signOut, type User } from "firebase/auth";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { auth, isFirebaseConfigured } from "../lib/firebase";

const publicRoutes = ["/signin", "/terms", "/privacy", "/cookies", "/disclaimer"];
const TERMS_VERSION = "2026-08-11";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const isPublic = publicRoutes.some((route) => path === route || path.startsWith(`${route}/`));
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(!isPublic);
  const [termsAccepted, setTermsAccepted] = useState(isPublic);

  const acknowledgementKey = useMemo(() => {
    if (!user) return "";
    return `stoxcheck:terms:${TERMS_VERSION}:${user.uid}:${user.metadata.lastSignInTime ?? "session"}`;
  }, [user]);

  useEffect(() => {
    if (isPublic) {
      setChecking(false);
      return;
    }
    if (!auth) {
      setChecking(false);
      return;
    }
    return onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setChecking(false);
      if (!nextUser) router.replace(`/signin?next=${encodeURIComponent(path)}`);
    });
  }, [isPublic, path, router]);

  useEffect(() => {
    if (!acknowledgementKey) return;
    setTermsAccepted(sessionStorage.getItem(acknowledgementKey) === "accepted");
  }, [acknowledgementKey]);

  if (isPublic) return children;
  if (checking) return <div className="auth-state">Checking your secure session…</div>;
  if (!isFirebaseConfigured || !auth) return <div className="auth-state error">
    Firebase Authentication is not configured. Add the required Vercel environment variables.
  </div>;
  if (!user) return <div className="auth-state">Taking you to sign in…</div>;

  const acceptTerms = () => {
    sessionStorage.setItem(acknowledgementKey, "accepted");
    setTermsAccepted(true);
  };

  const logOut = async () => {
    sessionStorage.removeItem(acknowledgementKey);
    if (!auth) return;
    await signOut(auth);
    router.replace("/signin");
  };

  return <>
    <div className="account-strip">
      <span>Private Stoxcheck session</span>
      <button type="button" onClick={logOut}>Sign out</button>
    </div>
    {children}
    {!termsAccepted && <div className="terms-overlay" role="dialog" aria-modal="true" aria-labelledby="terms-title">
      <div className="terms-modal">
        <p className="eyebrow">Required each time you sign in</p>
        <h2 id="terms-title">Before using Stoxcheck.</h2>
        <p>Stoxcheck provides experimental automated news-sentiment estimates for information and
          education only. It is not financial, investment, legal, tax or trading advice. Outputs
          may be wrong, delayed, incomplete or based on very few headlines. Do not make an
          investment decision from Stoxcheck alone.</p>
        <p>By continuing, you confirm that you have read and accept the <Link href="/terms" target="_blank">Terms</Link>,
          acknowledge the <Link href="/disclaimer" target="_blank">Financial Disclaimer</Link>, and
          have reviewed how information is handled in the <Link href="/privacy" target="_blank">Privacy and Data Usage Notice</Link>.</p>
        <button type="button" onClick={acceptTerms}>I understand and agree</button>
        <small>Terms version {TERMS_VERSION}. This acknowledgement is kept only for this browser login session.</small>
      </div>
    </div>}
  </>;
}
