/** Calls the Stoxcheck API. */
import { Aggregate, Snapshot } from "./types";
import { auth } from "./firebase";

type ManualPrediction = {
  sentiment: "positive" | "neutral" | "negative";
  confidence: number;
};

export const stocks = [
  ["AAPL","Apple"],["NVDA","Nvidia"],["GOOG","Alphabet"],["MSFT","Microsoft"],
  ["AMZN","Amazon"],["AVGO","Broadcom"],["META","Meta Platforms"],["SPCX","SpaceX"],
  ["TSLA","Tesla"],["LLY","Eli Lilly"],
] as const;

const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8080";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  // Cloud Run can take a moment to wake up, so give it one more go.
  let lastProblem: unknown;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12_000);
    try {
      const token = auth?.currentUser ? await auth.currentUser.getIdToken() : null;
      const headers = new Headers(init?.headers);
      if (token) headers.set("Authorization", `Bearer ${token}`);
      const response = await fetch(url, {...init, headers, signal: controller.signal});
      if (response.ok) return await response.json() as T;
      if (response.status < 500 || attempt === 1) {
        throw new Error(`Request failed with status ${response.status}.`);
      }
      lastProblem = new Error(`Temporary service response ${response.status}.`);
    } catch (problem) {
      lastProblem = problem;
      if (attempt === 1) break;
    } finally {
      window.clearTimeout(timeout);
    }
    await new Promise(resolve => window.setTimeout(resolve, 350));
  }
  throw lastProblem instanceof Error ? lastProblem : new Error("The service could not be reached.");
}

export async function getSnapshot(ticker: string): Promise<Snapshot> {
  try {
    return await fetchJson<Snapshot>(`${base}/v1/stocks/${ticker}/latest`, {cache: "no-store"});
  } catch {
    throw new Error("Current sentiment is temporarily unavailable.");
  }
}

export async function getHistory(ticker: string, period = "daily") {
  const payload = await fetchJson<{values: Aggregate[]}>(
    `${base}/v1/stocks/${ticker}/history?period=${period}&limit=20`,
    {cache: "no-store"},
  );
  return payload.values.reverse();
}

export async function checkHeadline(headline: string, target?: string): Promise<ManualPrediction> {
  // target is optional because the website's quick checker doesn't ask for one.
  const payload = await fetchJson<{predictions: ManualPrediction[]}>(`${base}/v1/predict`, {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({headlines:[headline], target: target || null}),
  });
  return payload.predictions[0];
}
