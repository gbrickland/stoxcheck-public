import Link from "next/link";
import SiteFooter from "./SiteFooter";

export default function LegalPage({ eyebrow, title, updated = "11 August 2026", children }: {
  eyebrow: string; title: string; updated?: string; children: React.ReactNode;
}) {
  return <main className="legal-shell">
    <header className="legal-header"><Link className="brand" href="/">stoxcheck<span>.</span></Link><Link href="/signin">Sign in</Link></header>
    <article className="legal-page">
      <p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="legal-updated">Last updated: {updated}</p>
      <div className="legal-callout"><strong>Important:</strong> Stoxcheck is an experimental academic project, not a regulated financial adviser. Nothing on this site is financial advice.</div>
      {children}
    </article>
    <SiteFooter/>
  </main>;
}
