"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface PullsPageProps {
  params: Promise<{ owner: string; repo: string }>;
}

export default function PullsPage({ params }: PullsPageProps) {
  const { owner, repo } = use(params);
  const queryClient = useQueryClient();

  const { data: pulls, isLoading } = useQuery({
    queryKey: ["pulls", owner, repo],
    queryFn: () => api.github.listPullRequests(owner, repo),
  });

  const reviewMutation = useMutation({
    mutationFn: (prNumber: number) =>
      api.github.reviewPullRequest(owner, repo, prNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pulls", owner, repo] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading pull requests...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Link href="/github" className="hover:text-foreground">
            GitHub
          </Link>
          <span>/</span>
          <Link href={`/github/${owner}/${repo}`} className="hover:text-foreground">
            {owner}/{repo}
          </Link>
          <span>/</span>
          <span className="text-foreground">Pull Requests</span>
        </div>
        <h1 className="mt-1 text-2xl font-bold">Pull Requests</h1>
      </div>

      {!pulls || pulls.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted">No open pull requests</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pulls.map((pr) => (
            <div
              key={pr.number}
              className="rounded-lg border border-border p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-muted">#{pr.number}</span>
                    <h3 className="font-medium truncate">{pr.title}</h3>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-sm text-muted">
                    <div className="flex items-center gap-1">
                      {pr.user_avatar && (
                        <img
                          src={pr.user_avatar}
                          alt={pr.user_login}
                          className="h-4 w-4 rounded-full"
                        />
                      )}
                      <span>{pr.user_login}</span>
                    </div>
                    <span>{pr.head_ref} → {pr.base_ref}</span>
                    <span className="text-green-500">+{pr.additions}</span>
                    <span className="text-severity-error">-{pr.deletions}</span>
                    <span>{pr.changed_files} files</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => reviewMutation.mutate(pr.number)}
                    disabled={reviewMutation.isPending}
                    className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
                  >
                    {reviewMutation.isPending ? "..." : "Review"}
                  </button>
                  <a
                    href={pr.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-medium hover:bg-secondary/80"
                  >
                    View on GitHub
                  </a>
                </div>
              </div>

              <Link
                href={`/github/${owner}/${repo}/pulls/${pr.number}`}
                className="mt-3 block text-sm text-primary hover:underline"
              >
                View AI reviews →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
