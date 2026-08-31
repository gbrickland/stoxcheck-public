/** Stable JSON contracts shared by the dashboard components and API client. */
export type Probabilities = { positive: number; neutral: number; negative: number };

export type Aggregate = {
  window_start: string;
  window_end: string;
  headline_count: number;
  average_sentiment: number;
  average_confidence?: number;
  sentiment_volatility: number;
  average_probabilities: Probabilities;
};

export type Headline = {
  headline: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: "positive" | "neutral" | "negative";
  confidence: number;
  probabilities: Probabilities;
};

export type Snapshot = {
  ticker: string;
  company: string;
  generated_at: string;
  hourly: Aggregate | null;
  daily: Aggregate | null;
  weekly: Aggregate | null;
  recent_headlines: Headline[];
};
