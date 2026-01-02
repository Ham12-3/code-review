"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { CodeEditor } from "@/components/CodeEditor";
import { ReviewResults } from "@/components/ReviewResults";
import { cn } from "@/lib/utils";

interface ReviewPageProps {
  params: Promise<{ id: string }>;
}

export default function ReviewPage({ params }: ReviewPageProps) {
  const { id } = use(params);
  const reviewId = parseInt(id, 10);
  const queryClient = useQueryClient();
  const [useComplexModel, setUseComplexModel] = useState(false);

  const { data: review, isLoading, error } = useQuery({
    queryKey: ["review", reviewId],
    queryFn: () => api.getReview(reviewId),
    refetchInterval: (query) => {
      // Poll while analyzing
      const data = query.state.data;
      return data?.status === "analyzing" ? 2000 : false;
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeReview(reviewId, useComplexModel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review", reviewId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading review...</div>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="rounded-lg border border-severity-error/50 bg-severity-error/10 p-4">
        <p className="text-severity-error">Failed to load review</p>
      </div>
    );
  }

  const canAnalyze = review.status === "pending" || review.status === "failed";
  const isAnalyzing = review.status === "analyzing";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {review.filename || `Review #${review.id}`}
          </h1>
          <p className="mt-1 text-muted">
            {review.language || "Unknown language"} •{" "}
            {new Date(review.created_at).toLocaleDateString()}
          </p>
        </div>
        <StatusBadge status={review.status} />
      </div>

      {canAnalyze && (
        <div className="flex items-center gap-4 rounded-lg border border-border bg-secondary p-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={useComplexModel}
              onChange={(e) => setUseComplexModel(e.target.checked)}
              className="rounded border-border"
            />
            <span className="text-sm">
              Use Claude Opus (complex analysis)
            </span>
          </label>
          <button
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
            className="ml-auto rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {analyzeMutation.isPending ? "Starting..." : "Start Analysis"}
          </button>
        </div>
      )}

      {isAnalyzing && (
        <div className="rounded-lg border border-primary/50 bg-primary/10 p-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Analysis in progress...</span>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-4 text-lg font-semibold">Code</h2>
          <div className="rounded-lg border border-border overflow-hidden">
            <CodeEditor
              value={review.code_content}
              language={review.language || "plaintext"}
              height="500px"
              readOnly
              highlightedLines={review.comments.map((c) => ({
                start: c.line_start,
                end: c.line_end,
                severity: c.severity,
              }))}
            />
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-lg font-semibold">Results</h2>
          <ReviewResults
            result={review.result}
            comments={review.comments}
            status={review.status}
          />
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles = {
    pending: "bg-muted/20 text-muted",
    analyzing: "bg-primary/20 text-primary",
    completed: "bg-green-500/20 text-green-500",
    failed: "bg-severity-error/20 text-severity-error",
  };

  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 text-sm font-medium capitalize",
        styles[status as keyof typeof styles]
      )}
    >
      {status}
    </span>
  );
}
