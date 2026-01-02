"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function GitHubPage() {
  const queryClient = useQueryClient();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const { data: installations, isLoading, error } = useQuery({
    queryKey: ["github-installations"],
    queryFn: () => api.github.listInstallations(),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.github.syncInstallations(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["github-installations"] });
      setSyncMessage(`Synced: ${data.installations.length > 0 ? data.installations.join(", ") : "No installations found"}`);
      setTimeout(() => setSyncMessage(null), 5000);
    },
    onError: (err: Error) => {
      setSyncMessage(`Error: ${err.message}`);
      setTimeout(() => setSyncMessage(null), 5000);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted">Loading installations...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-severity-error/50 bg-severity-error/10 p-4">
        <p className="text-severity-error">Failed to load GitHub installations</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">GitHub Integration</h1>
          <p className="mt-2 text-muted">
            Connect your repositories for automated code review
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="rounded-lg border border-border px-4 py-2 font-medium hover:bg-secondary disabled:opacity-50"
          >
            {syncMutation.isPending ? "Syncing..." : "Sync from GitHub"}
          </button>
          <a
            href="https://github.com/apps/code-review-local/installations/new"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover"
          >
            Install GitHub App
          </a>
        </div>
      </div>

      {syncMessage && (
        <div className={cn(
          "rounded-lg border p-3 text-sm",
          syncMessage.startsWith("Error")
            ? "border-severity-error/50 bg-severity-error/10 text-severity-error"
            : "border-primary/50 bg-primary/10 text-primary"
        )}>
          {syncMessage}
        </div>
      )}

      {installations?.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <div className="mx-auto mb-4 h-12 w-12 text-muted">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
          </div>
          <p className="text-muted">No GitHub installations found</p>
          <p className="mt-2 text-sm text-muted">
            Install the app, then click "Sync from GitHub" above
          </p>
          <a
            href="https://github.com/apps/code-review-local/installations/new"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-block text-primary hover:underline"
          >
            Install the GitHub App to get started
          </a>
        </div>
      ) : (
        <div className="space-y-6">
          {installations?.map((installation) => (
            <div
              key={installation.id}
              className="rounded-lg border border-border p-6"
            >
              <div className="mb-4 flex items-center gap-4">
                {installation.account_avatar_url && (
                  <img
                    src={installation.account_avatar_url}
                    alt={installation.account_login}
                    className="h-12 w-12 rounded-full"
                  />
                )}
                <div>
                  <h2 className="text-xl font-semibold">
                    {installation.account_login}
                  </h2>
                  <span className="text-sm text-muted">
                    {installation.account_type}
                  </span>
                </div>
              </div>

              {installation.repositories.length === 0 ? (
                <p className="text-muted">No repositories connected</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {installation.repositories.map((repo) => (
                    <Link
                      key={repo.id}
                      href={`/github/${repo.full_name}`}
                      className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/50 hover:bg-secondary"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">
                          {repo.full_name.split("/")[1]}
                        </p>
                        <p className="text-xs text-muted truncate">
                          {repo.language || "Unknown"} •{" "}
                          {repo.private ? "Private" : "Public"}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
