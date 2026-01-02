"use client";

import { cn } from "@/lib/utils";

interface ReviewComment {
  id: number;
  line_start: number;
  line_end: number;
  content: string;
  severity: string;
  category: string | null;
  suggestion: string | null;
}

interface ReviewResult {
  id: number;
  summary: string;
  issues_found: number;
  security_issues: number;
  quality_score: number | null;
  ai_model_used: string;
  processing_time_ms: number | null;
}

interface ReviewResultsProps {
  result: ReviewResult | null;
  comments: ReviewComment[];
  status: string;
}

export function ReviewResults({ result, comments, status }: ReviewResultsProps) {
  if (status === "pending") {
    return (
      <div className="rounded-lg border border-border bg-secondary p-6 text-center">
        <p className="text-muted">
          Click &quot;Start Analysis&quot; to review this code
        </p>
      </div>
    );
  }

  if (status === "analyzing") {
    return (
      <div className="rounded-lg border border-border bg-secondary p-6">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted">Analyzing code...</p>
        </div>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="rounded-lg border border-severity-error/50 bg-severity-error/10 p-6">
        <p className="text-severity-error">Analysis failed. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {result && <SummaryCard result={result} />}

      <div className="space-y-4">
        <h3 className="font-semibold">
          Issues ({comments.length})
        </h3>
        {comments.length === 0 ? (
          <div className="rounded-lg border border-green-500/50 bg-green-500/10 p-4">
            <p className="text-green-500">No issues found!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {comments.map((comment) => (
              <IssueCard key={comment.id} comment={comment} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ result }: { result: ReviewResult }) {
  return (
    <div className="rounded-lg border border-border bg-secondary p-4">
      <div className="mb-4 grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold">{result.issues_found}</div>
          <div className="text-xs text-muted">Issues</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-severity-error">
            {result.security_issues}
          </div>
          <div className="text-xs text-muted">Security</div>
        </div>
        <div>
          <div className="text-2xl font-bold">
            {result.quality_score ?? "N/A"}
          </div>
          <div className="text-xs text-muted">Quality</div>
        </div>
      </div>

      <p className="text-sm">{result.summary}</p>

      <div className="mt-4 flex items-center justify-between text-xs text-muted">
        <span>Model: {result.ai_model_used}</span>
        {result.processing_time_ms && (
          <span>{(result.processing_time_ms / 1000).toFixed(1)}s</span>
        )}
      </div>
    </div>
  );
}

function IssueCard({ comment }: { comment: ReviewComment }) {
  const severityStyles = {
    info: "border-severity-info/50 bg-severity-info/10",
    warning: "border-severity-warning/50 bg-severity-warning/10",
    error: "border-severity-error/50 bg-severity-error/10",
    critical: "border-severity-critical/50 bg-severity-critical/10",
  };

  const severityTextStyles = {
    info: "text-severity-info",
    warning: "text-severity-warning",
    error: "text-severity-error",
    critical: "text-severity-critical",
  };

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        severityStyles[comment.severity as keyof typeof severityStyles]
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <span
          className={cn(
            "text-xs font-medium uppercase",
            severityTextStyles[comment.severity as keyof typeof severityTextStyles]
          )}
        >
          {comment.severity}
        </span>
        <span className="text-xs text-muted">
          Line {comment.line_start}
          {comment.line_end !== comment.line_start && `-${comment.line_end}`}
        </span>
      </div>

      {comment.category && (
        <span className="mb-2 inline-block rounded bg-secondary px-2 py-0.5 text-xs">
          {comment.category}
        </span>
      )}

      <p className="text-sm">{comment.content}</p>

      {comment.suggestion && (
        <div className="mt-3 rounded bg-background/50 p-2">
          <span className="text-xs font-medium text-muted">Suggestion:</span>
          <p className="mt-1 text-sm">{comment.suggestion}</p>
        </div>
      )}
    </div>
  );
}
