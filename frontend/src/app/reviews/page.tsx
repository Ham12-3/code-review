"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_STYLES = {
  pending: "bg-muted/20 text-muted",
  analyzing: "bg-primary/20 text-primary",
  completed: "bg-green-500/20 text-green-500",
  failed: "bg-severity-error/20 text-severity-error",
};

export default function ReviewsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.listReviews(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading reviews...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-severity-error/50 bg-severity-error/10 p-4">
        <p className="text-severity-error">Failed to load reviews</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Reviews</h1>
        <Link
          href="/"
          className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover"
        >
          New Review
        </Link>
      </div>

      {data?.items.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted">No reviews yet</p>
          <Link href="/" className="mt-2 text-primary hover:underline">
            Create your first review
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {data?.items.map((review) => (
            <Link
              key={review.id}
              href={`/reviews/${review.id}`}
              className="block rounded-lg border border-border p-4 transition-colors hover:border-primary/50"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium">
                    {review.filename || `Review #${review.id}`}
                  </h3>
                  <p className="mt-1 text-sm text-muted">
                    {review.language || "Unknown language"} •{" "}
                    {new Date(review.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium capitalize",
                    STATUS_STYLES[review.status]
                  )}
                >
                  {review.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {data && data.total > data.page_size && (
        <div className="flex justify-center">
          <p className="text-sm text-muted">
            Showing {data.items.length} of {data.total} reviews
          </p>
        </div>
      )}
    </div>
  );
}
