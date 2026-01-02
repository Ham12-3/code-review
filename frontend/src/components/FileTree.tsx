"use client";

import { cn } from "@/lib/utils";

interface FileTreeItem {
  name: string;
  path: string;
  type: string;
  size?: number;
}

interface FileTreeProps {
  items: FileTreeItem[];
  onItemClick: (path: string, type: string) => void;
  selectedPath?: string | null;
}

export function FileTree({ items, onItemClick, selectedPath }: FileTreeProps) {
  // Sort: directories first, then files alphabetically
  const sortedItems = [...items].sort((a, b) => {
    if (a.type === "dir" && b.type !== "dir") return -1;
    if (a.type !== "dir" && b.type === "dir") return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="space-y-1">
      {sortedItems.map((item) => (
        <button
          key={item.path}
          onClick={() => onItemClick(item.path, item.type)}
          className={cn(
            "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-secondary",
            selectedPath === item.path && "bg-primary/20 text-primary"
          )}
        >
          {item.type === "dir" ? (
            <FolderIcon className="h-4 w-4 text-primary" />
          ) : (
            <FileIcon className="h-4 w-4 text-muted" extension={item.name.split(".").pop()} />
          )}
          <span className="flex-1 truncate">{item.name}</span>
          {item.type === "file" && item.size !== undefined && (
            <span className="text-xs text-muted">
              {formatSize(item.size)}
            </span>
          )}
        </button>
      ))}

      {items.length === 0 && (
        <div className="py-4 text-center text-sm text-muted">
          Empty directory
        </div>
      )}
    </div>
  );
}

function FolderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}

function FileIcon({ className, extension }: { className?: string; extension?: string }) {
  // Color based on file type
  const colors: Record<string, string> = {
    ts: "text-blue-400",
    tsx: "text-blue-400",
    js: "text-yellow-400",
    jsx: "text-yellow-400",
    py: "text-green-400",
    go: "text-cyan-400",
    rs: "text-orange-400",
    java: "text-red-400",
    md: "text-muted",
    json: "text-yellow-500",
    yml: "text-purple-400",
    yaml: "text-purple-400",
  };

  const color = extension ? colors[extension] || "text-muted" : "text-muted";

  return (
    <svg
      className={cn(className, color)}
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
