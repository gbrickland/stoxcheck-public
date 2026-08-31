"use client";

/** The small form for trying one headline by hand. */
import { FormEvent, useState } from "react";
import { checkHeadline } from "../lib/api";

type PredictionResult = {
  sentiment: "positive" | "neutral" | "negative";
  confidence: number;
};

export default function HeadlineChecker() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    // Only replace the last answer when the new check works.
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await checkHeadline(text));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Prediction failed.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="checker">
    <div>
      <p className="eyebrow">Check a headline yourself</p>
      <h2>What does the model think?</h2>
      <p>Paste in a financial headline and Stoxcheck will rate its tone.</p>
    </div>
    <form onSubmit={submit}>
      <input
        value={text}
        onChange={event => setText(event.target.value)}
        required
        maxLength={1000}
        placeholder="Company raises guidance after record quarterly sales"
      />
      <button disabled={busy}>{busy ? "Checking…" : "Check →"}</button>
    </form>
    {error && <p className="error">{error}</p>}
    {result && <div className={`checker-result ${result.sentiment}`}>
      <strong>{result.sentiment}</strong>
      <span>{Math.round(result.confidence * 100)}% confidence</span>
    </div>}
  </section>;
}
