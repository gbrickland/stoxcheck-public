"use client";

/** Main dashboard. */
import { useCallback, useEffect, useState } from "react";
import HeadlineChecker from "../components/HeadlineChecker";
import Score from "../components/Score";
import SiteFooter from "../components/SiteFooter";
import { getHistory, getSnapshot, stocks } from "../lib/api";
import { Aggregate, Snapshot } from "../lib/types";

export default function Home() {
  const [ticker, setTicker] = useState("AAPL");
  const [data, setData] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<Aggregate[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [headlinePhase, setHeadlinePhase] = useState<"idle" | "leaving" | "entering">("idle");

  const loadTicker = useCallback(async (background = false) => {
    // A refresh only swaps the news list. A new ticker replaces the whole view.
    if (background) {
      setRefreshing(true);
      setHeadlinePhase("leaving");
      await new Promise((resolve) => window.setTimeout(resolve, 230));
    } else {
      setLoading(true);
    }
    setError("");
    try {
      // Keep the current reading available if history fails.
      const [snapshotResult, historyResult] = await Promise.allSettled([
        getSnapshot(ticker),
        getHistory(ticker),
      ]);
      if (snapshotResult.status === "rejected") throw snapshotResult.reason;
      setData(snapshotResult.value);
      setHistory(historyResult.status === "fulfilled" ? historyResult.value : []);
      if (background) {
        setHeadlinePhase("entering");
        window.setTimeout(() => setHeadlinePhase("idle"), 1200);
      }
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Current sentiment is temporarily unavailable.");
      setHeadlinePhase("idle");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [ticker]);

  useEffect(() => {
    loadTicker();
  }, [loadTicker]);

  // Positive probability minus negative probability, scaled to -100..+100.
  const current = data?.hourly?.average_sentiment ?? 0;
  const sentimentPercentage = Math.max(-100, Math.min(100, current * 100));
  const averageProbabilities = data?.hourly?.average_probabilities;
  const negativeShare = (averageProbabilities?.negative ?? 0) * 100;
  const neutralShare = (averageProbabilities?.neutral ?? 1) * 100;
  const positiveShare = (averageProbabilities?.positive ?? 0) * 100;
  const averageConfidence = data?.hourly?.average_confidence != null
    ? data.hourly.average_confidence * 100
    : averageProbabilities
      ? Math.max(
        averageProbabilities.positive,
        averageProbabilities.neutral,
        averageProbabilities.negative
      ) * 100
      : 0;
  const reading = current > .12 ? "Positive" : current < -.12 ? "Negative" : "Neutral";
  const selectedCompany = data?.company ?? stocks.find(([symbol]) => symbol === ticker)?.[1] ?? ticker;
  // Keep the newest headlines first.
  const recentHeadlines = [...(data?.recent_headlines ?? [])].sort(
    (left, right) => new Date(right.published_at).getTime() - new Date(left.published_at).getTime()
  );

  return <main>
    <header>
      <a className="brand">stoxcheck<span>.</span></a>
      <nav><a href="#market">Market</a><a href="#headlines">Headlines</a><a href="#checker">Model</a></nav>
      <span className="live"><i/>Active</span>
    </header>

    <section className="hero">
      <div>
        <p className="eyebrow">News sentiment for 10 US companies</p>
        <h1>See how the latest<br/>stock news feels.</h1>
        <p>Stoxcheck gathers recent company headlines from different publishers and checks whether they sound positive, neutral or negative. The results are brought together into hourly, daily and weekly readings.</p>
      </div>
    </section>

    <section className="reading" aria-label="Current sentiment reading">
      <div className="reading-copy">
        <p className="eyebrow">Latest result</p>
        <h2>{selectedCompany}.</h2>
        <h3>Current reading.</h3>
        <p>This reading brings together the recent headlines found for this company during the latest hourly window.</p>
      </div>
      <div
        className="hero-stat"
        aria-label={`${reading}; sentiment index ${sentimentPercentage.toFixed(0)}; ${positiveShare.toFixed(0)} percent positive, ${neutralShare.toFixed(0)} percent neutral, ${negativeShare.toFixed(0)} percent negative`}
      >
        <svg className="sentiment-donut hero-donut" viewBox="0 0 100 100" aria-hidden="true">
          {positiveShare > 0 && <circle className="donut-segment donut-positive" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, positiveShare - 3.5)} 100`} strokeDashoffset="0"/>}
          {neutralShare > 0 && <circle className="donut-segment donut-neutral" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, neutralShare - 3.5)} 100`} strokeDashoffset={-positiveShare}/>}
          {negativeShare > 0 && <circle className="donut-segment donut-negative" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, negativeShare - 3.5)} 100`} strokeDashoffset={-(positiveShare + neutralShare)}/>}
        </svg>
        <span>Sentiment index</span>
        <strong className={sentimentPercentage > 0 ? "positive" : sentimentPercentage < 0 ? "negative" : "neutral"}>
          {sentimentPercentage > 0 ? "+" : ""}{sentimentPercentage.toFixed(0)}
        </strong>
        <b className={`hero-stat-outcome ${reading.toLowerCase()}`}>{reading}</b>
        <div className="hero-stat-mix" aria-label="Average sentiment probabilities">
          <span className="mix-negative"><i/>Negative <b>{negativeShare.toFixed(0)}%</b></span>
          <span className="mix-neutral"><i/>Neutral <b>{neutralShare.toFixed(0)}%</b></span>
          <span className="mix-positive"><i/>Positive <b>{positiveShare.toFixed(0)}%</b></span>
        </div>
        <div className="hero-stat-details">
          <p><span>Avg confidence</span><b>{averageConfidence.toFixed(0)}%</b></p>
          <p><span>Headlines</span><b>{data?.hourly?.headline_count ?? 0}</b></p>
        </div>
      </div>
    </section>

    <section id="market">
      <div className="section-head">
        <div><p className="eyebrow">Companies tracked</p><h2>Choose a company.</h2></div>
        <p>Headlines are checked every five minutes while the US market is open.</p>
      </div>
      <div className="tickers">
        {stocks.map(([symbol, name]) =>
          <button key={symbol} className={ticker === symbol ? "selected" : ""} onClick={() => setTicker(symbol)}>
            <strong>{symbol}</strong><span>{name}</span>
          </button>
        )}
      </div>
    </section>

    {loading && <div className="state">Loading current sentiment…</div>}
    {error && <div className="state error">{error}</div>}
    {data && !loading && <section className="stock">
      <div className="stock-title">
        <div><p className="eyebrow">Latest figures</p><h2>{data.company} <span>{data.ticker}</span></h2></div>
        <small>Updated {new Date(data.generated_at).toLocaleTimeString()}</small>
      </div>
      <div className="scores">
        <Score label="Hourly" value={data.hourly}/>
        <Score label="Daily" value={data.daily}/>
        <Score label="Weekly" value={data.weekly}/>
      </div>
      <div className="probability">
        <span>Negative</span>
        <div>
          <i style={{width: `${(data.hourly?.average_probabilities.negative || 0) * 100}%`}}/>
          <i style={{width: `${(data.hourly?.average_probabilities.neutral || 0) * 100}%`}}/>
          <i style={{width: `${(data.hourly?.average_probabilities.positive || 0) * 100}%`}}/>
        </div>
        <span>Positive</span>
      </div>
      <div className="history">
        <div>
          <p className="eyebrow">Longer-term view</p>
          <h2>Daily sentiment history.</h2>
          <p>These daily readings are kept so changes can be compared over time. Old headline text is not stored with them.</p>
        </div>
        <div className="history-chart">
          {history.map((item, index) => {
            const score = item.average_sentiment;
            return <div className="history-column" key={`${item.window_start}-${index}`}>
              <span>{score.toFixed(2)}</span>
              <i className={score > .12 ? "up" : score < -.12 ? "down" : "flat"} style={{height: `${Math.max(8, Math.abs(score) * 110)}px`}}/>
              <small>{new Date(item.window_start).toLocaleDateString(undefined, {weekday: "short"})}</small>
            </div>;
          })}
        </div>
      </div>
      <div id="headlines" className="headlines">
        <div className="section-head">
          <div><p className="eyebrow">From different publishers</p><h2>Recent headlines.</h2></div>
          <button className="refresh-button" type="button" onClick={() => loadTicker(true)} disabled={refreshing}>
            <span aria-hidden="true">{refreshing ? "↻" : "⟳"}</span>
            {refreshing ? "Refreshing…" : "Refresh headlines"}
          </button>
        </div>
        <div className={`headline-items ${headlinePhase}`}>
          {recentHeadlines.length
            ? recentHeadlines.map((item, index) =>
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                key={`${item.headline}-${index}`}
                style={{animationDelay: `${index * 75}ms`}}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3>{item.headline}</h3>
                  <p>{item.source} · {new Date(item.published_at).toLocaleString(undefined, {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}</p>
                </div>
                <div className="headline-reading">
                  <b className={item.sentiment}>{item.sentiment}</b>
                  <span>Certainty <strong>{Math.round(item.confidence * 100)}%</strong></span>
                </div>
              </a>
            )
            : <p>No recent headlines are retained for this stock.</p>}
        </div>
      </div>
    </section>}

    <div id="checker"><HeadlineChecker/></div>
    <SiteFooter/>
  </main>;
}
