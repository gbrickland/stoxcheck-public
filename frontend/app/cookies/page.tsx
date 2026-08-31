import LegalPage from "../../components/LegalPage";

export default function CookiesPage() { return <LegalPage eyebrow="Browser storage" title="Cookie notice">
  <h2>1. Current use</h2><p>Stoxcheck uses only storage needed to authenticate restricted users, protect sessions and remember that the current terms were acknowledged for the current login. It does not currently operate advertising, behavioural profiling or optional analytics cookies.</p>
  <h2>2. Firebase Authentication</h2><p>Firebase Authentication uses browser persistence such as IndexedDB/local storage and may use cookies or equivalent identifiers to keep a user securely signed in, refresh authentication tokens and prevent abuse. These items are necessary to provide the requested account service.</p>
  <h2>3. Terms acknowledgement</h2><p>A session-storage value containing the terms version, Firebase user identifier and last-sign-in timestamp records that the current modal was acknowledged. It expires with the browser session or is removed on sign-out. It is not sent to advertisers.</p>
  <h2>4. Hosting and security</h2><p>Vercel and Google may process technical identifiers required for delivery, load balancing, security and fraud prevention. Their own notices provide further information.</p>
  <h2>5. Controlling storage</h2><p>You can clear site data through browser settings, but doing so may sign you out and cause the terms notice to appear again. Blocking required authentication storage may prevent Stoxcheck from working.</p>
  <h2>6. Future optional technologies</h2><p>If non-essential analytics, advertising or similar technologies are added, they must remain disabled until a clear consent choice is provided and this notice is updated. Guidance is available from the <a href="https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/" target="_blank" rel="noreferrer">ICO cookies guidance</a>.</p>
</LegalPage>; }
