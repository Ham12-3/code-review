"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

// Dynamic import for Monaco Editor - required for Next.js
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-secondary">
      <span className="text-muted">Loading editor...</span>
    </div>
  ),
});

interface HighlightedLine {
  start: number;
  end: number;
  severity: string;
}

interface CodeEditorProps {
  value: string;
  onChange?: (value: string) => void;
  language?: string;
  height?: string;
  readOnly?: boolean;
  highlightedLines?: HighlightedLine[];
}

export function CodeEditor({
  value,
  onChange,
  language = "plaintext",
  height = "400px",
  readOnly = false,
  highlightedLines = [],
}: CodeEditorProps) {
  const handleEditorMount = useMemo(
    () => (editor: unknown, monaco: unknown) => {
      // Add line decorations for highlighted issues
      if (highlightedLines.length > 0 && editor && monaco) {
        const monacoInstance = monaco as typeof import("monaco-editor");
        const editorInstance = editor as import("monaco-editor").editor.IStandaloneCodeEditor;

        const decorations = highlightedLines.map((line) => {
          const severityColors: Record<string, string> = {
            info: "rgba(59, 130, 246, 0.2)",
            warning: "rgba(245, 158, 11, 0.2)",
            error: "rgba(239, 68, 68, 0.2)",
            critical: "rgba(220, 38, 38, 0.3)",
          };

          return {
            range: new monacoInstance.Range(line.start, 1, line.end, 1),
            options: {
              isWholeLine: true,
              className: `highlight-${line.severity}`,
              glyphMarginClassName: `glyph-${line.severity}`,
              overviewRuler: {
                color: severityColors[line.severity] ?? severityColors.info,
                position: monacoInstance.editor.OverviewRulerLane.Full,
              },
            },
          };
        });

        editorInstance.deltaDecorations([], decorations);
      }
    },
    [highlightedLines]
  );

  return (
    <div className="monaco-editor-container" style={{ height }}>
      <MonacoEditor
        height="100%"
        language={mapLanguage(language)}
        value={value}
        onChange={(val) => onChange?.(val ?? "")}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: "on",
          padding: { top: 16, bottom: 16 },
          glyphMargin: highlightedLines.length > 0,
        }}
      />
    </div>
  );
}

// Map common language names to Monaco language IDs
function mapLanguage(language: string): string {
  const languageMap: Record<string, string> = {
    python: "python",
    py: "python",
    javascript: "javascript",
    js: "javascript",
    typescript: "typescript",
    ts: "typescript",
    tsx: "typescript",
    jsx: "javascript",
    java: "java",
    go: "go",
    golang: "go",
    rust: "rust",
    rs: "rust",
    c: "c",
    cpp: "cpp",
    "c++": "cpp",
    csharp: "csharp",
    cs: "csharp",
    ruby: "ruby",
    rb: "ruby",
    php: "php",
    html: "html",
    css: "css",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    markdown: "markdown",
    md: "markdown",
    sql: "sql",
    shell: "shell",
    bash: "shell",
    sh: "shell",
  };

  return languageMap[language.toLowerCase()] ?? "plaintext";
}
