/** One time-window card. The number is an index; the ring holds the three probabilities. */
import { Aggregate } from "../lib/types";

export default function Score({label, value}: {label:string; value:Aggregate|null}) {
  const score = value?.average_sentiment ?? 0;
  const scorePercent = Math.max(-100, Math.min(100, score * 100));
  const tone = score > .12 ? "positive" : score < -.12 ? "negative" : "neutral";
  const outcome = score > .12 ? "Positive" : score < -.12 ? "Negative" : "Neutral";
  const probabilities = value?.average_probabilities;
  const negative = (probabilities?.negative ?? 0) * 100;
  const neutral = (probabilities?.neutral ?? 1) * 100;
  const positive = (probabilities?.positive ?? 0) * 100;
  // Keep older Firestore rows working too.
  const confidence = value?.average_confidence != null
    ? value.average_confidence * 100
    : probabilities
      ? Math.max(probabilities.negative, probabilities.neutral, probabilities.positive) * 100
      : 0;

  return <article className="score">
    <span className="score-label">{label}</span>
    <div
      className="score-ring"
      aria-label={`${label}: sentiment index ${scorePercent.toFixed(0)}; ${negative.toFixed(0)} percent negative, ${neutral.toFixed(0)} percent neutral, ${positive.toFixed(0)} percent positive`}
    >
      <svg className="sentiment-donut score-ring-chart" viewBox="0 0 100 100" aria-hidden="true">
        {positive > 0 && <circle className="donut-segment donut-positive" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, positive - 3.5)} 100`} strokeDashoffset="0"/>}
        {neutral > 0 && <circle className="donut-segment donut-neutral" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, neutral - 3.5)} 100`} strokeDashoffset={-positive}/>}
        {negative > 0 && <circle className="donut-segment donut-negative" cx="50" cy="50" r="46" pathLength="100" strokeDasharray={`${Math.max(0, negative - 3.5)} 100`} strokeDashoffset={-(positive + neutral)}/>}
      </svg>
      <div className="score-ring-centre">
        <small>Sentiment index</small>
        <strong className={tone}>
          {scorePercent > 0 ? "+" : ""}{scorePercent.toFixed(0)}
        </strong>
        <b className={tone}>{outcome}</b>
      </div>
    </div>
    <div className="score-probabilities">
      <span className="negative-key"><i/>Negative <b>{negative.toFixed(0)}%</b></span>
      <span className="neutral-key"><i/>Neutral <b>{neutral.toFixed(0)}%</b></span>
      <span className="positive-key"><i/>Positive <b>{positive.toFixed(0)}%</b></span>
    </div>
    <div className="score-meta">
      <span><small>Avg confidence</small><b>{confidence.toFixed(0)}%</b></span>
      <span><small>Headlines</small><b>{value?.headline_count ?? 0}</b></span>
    </div>
  </article>;
}
