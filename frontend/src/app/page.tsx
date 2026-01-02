"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CodeEditor } from "@/components/CodeEditor";
import { api } from "@/lib/api";

const LANGUAGES = [
  { value: "", label: "Auto-detect" },
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "java", label: "Java" },
  { value: "go", label: "Go" },
  { value: "rust", label: "Rust" },
  { value: "cpp", label: "C++" },
  { value: "csharp", label: "C#" },
];

export default function HomePage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("");
  const [filename, setFilename] = useState("");

  const createReview = useMutation({
    mutationFn: () =>
      api.createReview({
        code_content: code,
        language: language || undefined,
        filename: filename || undefined,
      }),
    onSuccess: (data) => {
      router.push(`/reviews/${data.id}`);
    },
  });

  const handleSubmit = () => {
    if (!code.trim()) return;
    createReview.mutate();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Code Review</h1>
        <p className="mt-2 text-muted">
          Paste your code below for AI-powered analysis
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="language" className="mb-2 block text-sm font-medium">
            Language
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full rounded-lg border border-border bg-secondary px-4 py-2 focus:border-primary focus:outline-none"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="filename" className="mb-2 block text-sm font-medium">
            Filename (optional)
          </label>
          <input
            id="filename"
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="e.g., main.py"
            className="w-full rounded-lg border border-border bg-secondary px-4 py-2 focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <CodeEditor
          value={code}
          onChange={setCode}
          language={language || "plaintext"}
          height="400px"
        />
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleSubmit}
          disabled={!code.trim() || createReview.isPending}
          className="rounded-lg bg-primary px-6 py-2 font-medium text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createReview.isPending ? "Creating..." : "Submit for Review"}
        </button>
        {createReview.isError && (
          <p className="text-severity-error">
            Failed to create review. Please try again.
          </p>
        )}
      </div>
    </div>
  );
}
