"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface PRDetailPageProps {
  params: Promise<{ owner: string; repo: string; number: string }>;
}

const STATUS_STYLES = {
  pending: "bg-muted/20 text-muted",
  analyzing: "bg-primary/20 text-primary",
  completed: "bg-green-500/20 text-green-500",
  failed: "bg-severity-error/20 text-severity-error",
};

export default function PRDetailPage({ params }: PRDetailPageProps) {
  const { owner, repo, number } = use(params);
  const prNumber = parseInt(number, 10);
  const queryClient = useQueryClient();

  const { data: reviews, isLoading } = useQuery({
    queryKey: ["pr-reviews", owner, repo, prNumber],
    queryFn: () => api.github.listPRReviews(owner, repo, prNumber),
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasAnalyzing = data?.some((r) => r.status === "analyzing");
      return hasAnalyzing ? 3000 : false;
    },
  });

  const reviewMutation = useMutation({
    mutationFn: () => api.github.reviewPullRequest(owner, repo, prNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["pr-reviews", owner, repo, prNumber],
      });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading reviews...</div>
      </div>
    );
  }

  const latestReview = reviews?.[0];

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Link href="/github" className="hover:text-foreground">
            GitHub
          </Link>
          <span>/</span>
          <Link
            href={`/github/${owner}/${repo}`}
            className="hover:text-foreground"
          >
            {owner}/{repo}
          </Link>
          <span>/</span>
          <Link
            href={`/github/${owner}/${repo}/pulls`}
            className="hover:text-foreground"
          >
            Pull Requests
          </Link>
          <span>/</span>
          <span className="text-foreground">#{prNumber}</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <h1 className="text-2xl font-bold">
            {latestReview?.pr_title || `PR #${prNumber}`}
          </h1>
          {latestReview && (
            <span
              className={cn(
                "rounded-full px-3 py-1 text-sm font-medium capitalize",
                STATUS_STYLES[latestReview.status]
              )}
            >
              {latestReview.status}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => reviewMutation.mutate()}
          disabled={reviewMutation.isPending || latestReview?.status === "analyzing"}
          className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
        >
          {reviewMutation.isPending ? "Starting..." : "Run New Review"}
        </button>
        <a
          href={`https://github.com/${owner}/${repo}/pull/${prNumber}`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-secondary px-4 py-2 font-medium hover:bg-secondary/80"
        >
          View on GitHub
        </a>
      </div>

      {/* Latest Review Status */}
      {latestReview?.status === "analyzing" && (
        <div className="rounded-lg border border-primary/50 bg-primary/10 p-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Analysis in progress...</span>
          </div>
        </div>
      )}

      {latestReview?.status === "completed" && (
        <div className="rounded-lg border border-border bg-secondary p-6">
          <h3 className="mb-4 font-semibold">Latest Review Results</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-3xl font-bold">{latestReview.files_reviewed}</div>
              <div className="text-sm text-muted">Files Reviewed</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-severity-warning">
                {latestReview.issues_found}
              </div>
              <div className="text-sm text-muted">Issues Found</div>
            </div>
            <div>
              <div className="text-3xl font-bold">
                {latestReview.completed_at
                  ? new Date(latestReview.completed_at).toLocaleTimeString()
                  : "-"}
              </div>
              <div className="text-sm text-muted">Completed</div>
            </div>
          </div>

          {latestReview.github_review_id && (
            <div className="mt-4 text-center">
              <a
                href={`https://github.com/${owner}/${repo}/pull/${prNumber}#pullrequestreview-${latestReview.github_review_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                View Review on GitHub →
              </a>
            </div>
          )}
        </div>
      )}

      {latestReview?.status === "failed" && (
        <div className="rounded-lg border border-severity-error/50 bg-severity-error/10 p-4">
          <p className="font-medium text-severity-error">Review Failed</p>
          {latestReview.error_message && (
            <p className="mt-2 text-sm text-muted">{latestReview.error_message}</p>
          )}
        </div>
      )}

      {/* Review History */}
      {reviews && reviews.length > 1 && (
        <div>
          <h3 className="mb-4 font-semibold">Review History</h3>
          <div className="space-y-2">
            {reviews.slice(1).map((review) => (
              <div
                key={review.id}
                className="flex items-center justify-between rounded-lg border border-border p-3"
              >
                <div className="flex items-center gap-4">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                      STATUS_STYLES[review.status]
                    )}
                  >
                    {review.status}
                  </span>
                  <span className="text-sm text-muted">
                    {review.head_sha.slice(0, 7)}
                  </span>
                  <span className="text-sm">
                    {review.files_reviewed} files, {review.issues_found} issues
                  </span>
                </div>
                <span className="text-sm text-muted">
                  {new Date(review.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(!reviews || reviews.length === 0) && (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted">No reviews yet for this pull request</p>
          <button
            onClick={() => reviewMutation.mutate()}
            disabled={reviewMutation.isPending}
            className="mt-4 rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
          >
            Start First Review
          </button>
        </div>
      )}
    </div>
  );
}
