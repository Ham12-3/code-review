"use client";

import { use, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { FileTree } from "@/components/FileTree";
import { CodeEditor } from "@/components/CodeEditor";

interface RepoPageProps {
  params: Promise<{ owner: string; repo: string }>;
}

export default function RepoPage({ params }: RepoPageProps) {
  const { owner, repo } = use(params);
  const [currentPath, setCurrentPath] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const { data: contents, isLoading: contentsLoading } = useQuery({
    queryKey: ["repo-contents", owner, repo, currentPath],
    queryFn: () => api.github.getRepoContents(owner, repo, currentPath),
  });

  const { data: fileContent, isLoading: fileLoading } = useQuery({
    queryKey: ["file-content", owner, repo, selectedFile],
    queryFn: () =>
      selectedFile
        ? api.github.getFileContent(owner, repo, selectedFile)
        : null,
    enabled: !!selectedFile,
  });

  const reviewMutation = useMutation({
    mutationFn: (path: string) =>
      api.github.reviewFile(owner, repo, { path, use_complex_model: false }),
  });

  const handleFileClick = (path: string, type: string) => {
    if (type === "dir") {
      setCurrentPath(path);
      setSelectedFile(null);
    } else {
      setSelectedFile(path);
    }
  };

  const handleBack = () => {
    const parts = currentPath.split("/");
    parts.pop();
    setCurrentPath(parts.join("/"));
    setSelectedFile(null);
  };

  const handleReview = () => {
    if (selectedFile) {
      reviewMutation.mutate(selectedFile);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted">
            <Link href="/github" className="hover:text-foreground">
              GitHub
            </Link>
            <span>/</span>
            <span>{owner}</span>
            <span>/</span>
            <span className="text-foreground">{repo}</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold">{repo}</h1>
        </div>
        <Link
          href={`/github/${owner}/${repo}/pulls`}
          className="rounded-lg bg-secondary px-4 py-2 font-medium hover:bg-secondary/80"
        >
          Pull Requests
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* File Tree */}
        <div className="rounded-lg border border-border p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Files</h2>
            {currentPath && (
              <button
                onClick={handleBack}
                className="text-sm text-muted hover:text-foreground"
              >
                ← Back
              </button>
            )}
          </div>

          {currentPath && (
            <div className="mb-2 rounded bg-secondary px-2 py-1 text-sm text-muted">
              /{currentPath}
            </div>
          )}

          {contentsLoading ? (
            <div className="py-4 text-center text-muted">Loading...</div>
          ) : (
            <FileTree
              items={contents?.items || []}
              onItemClick={handleFileClick}
              selectedPath={selectedFile}
            />
          )}
        </div>

        {/* File Content / Preview */}
        <div className="lg:col-span-2">
          {selectedFile ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{selectedFile}</h3>
                <button
                  onClick={handleReview}
                  disabled={reviewMutation.isPending}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
                >
                  {reviewMutation.isPending ? "Starting..." : "Review This File"}
                </button>
              </div>

              {reviewMutation.isSuccess && (
                <div className="rounded-lg border border-green-500/50 bg-green-500/10 p-3">
                  <p className="text-green-500">
                    Review started!{" "}
                    <Link
                      href={`/reviews/${reviewMutation.data.review_id}`}
                      className="underline"
                    >
                      View results
                    </Link>
                  </p>
                </div>
              )}

              <div className="rounded-lg border border-border overflow-hidden">
                {fileLoading ? (
                  <div className="flex h-96 items-center justify-center text-muted">
                    Loading file...
                  </div>
                ) : fileContent ? (
                  <CodeEditor
                    value={fileContent.content}
                    language={fileContent.language || "plaintext"}
                    height="500px"
                    readOnly
                  />
                ) : null}
              </div>
            </div>
          ) : (
            <div className="flex h-96 items-center justify-center rounded-lg border border-border">
              <p className="text-muted">Select a file to preview</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
