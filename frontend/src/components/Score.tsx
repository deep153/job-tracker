import type { FitScore } from "../types/job";
import { timeAgo } from "../utils/format";
import { CheckIcon } from "./icons";

function scoreLevel(score: number): string {
  if (score >= 85) return "excellent";
  if (score >= 70) return "good";
  if (score >= 50) return "fair";
  return "poor";
}

export function ScoreBadge({ score }: { score: FitScore | null }) {
  if (score === null) {
    return (
      <span className="score score-none" title="Scored on the next run">
        <span className="visually-hidden">Not scored yet</span>
        <span aria-hidden="true">–</span>
      </span>
    );
  }
  return (
    <span
      className={`score score-${scoreLevel(score.score)}`}
      title={`Fit score ${score.score} of 100, by ${score.model}, ${timeAgo(score.scored_at)}`}
    >
      <span className="visually-hidden">Fit score </span>
      {score.score}
    </span>
  );
}

export function ScoreDetails({ score }: { score: FitScore }) {
  return (
    <div className="score-details">
      {score.reasons.length > 0 && (
        <ul className="score-reasons">
          {score.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      {(score.matched_keywords.length > 0 || score.missing_keywords.length > 0) && (
        <div className="keywords">
          {score.matched_keywords.length > 0 && (
            <span className="visually-hidden">Matched keywords: {score.matched_keywords.join(", ")}.</span>
          )}
          {score.matched_keywords.map((keyword) => (
            <span className="keyword keyword-matched" key={`m-${keyword}`} aria-hidden="true">
              <CheckIcon />
              {keyword}
            </span>
          ))}
          {score.missing_keywords.length > 0 && (
            <span className="visually-hidden">Missing keywords: {score.missing_keywords.join(", ")}.</span>
          )}
          {score.missing_keywords.map((keyword) => (
            <span className="keyword keyword-missing" key={`x-${keyword}`} aria-hidden="true" title="Not on your resume">
              {keyword}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
