import Link from "next/link";

/** Shared footer keeps legal material reachable from the dashboard and every policy page. */
export default function SiteFooter() {
  return <footer className="site-footer">
    <div><strong>Stoxcheck</strong><span>A university project for exploring stock-news sentiment · Not financial advice.</span></div>
    <nav aria-label="Legal and policy links">
      <Link href="/terms">Terms</Link>
      <Link href="/privacy">Privacy & data usage</Link>
      <Link href="/cookies">Cookies</Link>
      <Link href="/disclaimer">Financial disclaimer</Link>
    </nav>
  </footer>;
}
