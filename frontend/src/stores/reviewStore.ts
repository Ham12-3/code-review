import { create } from "zustand";

interface UIState {
  // Theme
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;

  // Editor preferences
  editorFontSize: number;
  setEditorFontSize: (size: number) => void;

  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;

  // Selected issue (for highlighting)
  selectedIssueId: number | null;
  setSelectedIssue: (id: number | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Theme
  theme: "dark",
  setTheme: (theme) => set({ theme }),

  // Editor preferences
  editorFontSize: 14,
  setEditorFontSize: (size) => set({ editorFontSize: size }),

  // Sidebar
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  // Selected issue
  selectedIssueId: null,
  setSelectedIssue: (id) => set({ selectedIssueId: id }),
}));

// Persist preferences to localStorage
if (typeof window !== "undefined") {
  const stored = localStorage.getItem("ui-preferences");
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      useUIStore.setState({
        theme: parsed.theme ?? "dark",
        editorFontSize: parsed.editorFontSize ?? 14,
      });
    } catch {
      // Invalid JSON, ignore
    }
  }

  // Subscribe to changes and persist
  useUIStore.subscribe((state) => {
    localStorage.setItem(
      "ui-preferences",
      JSON.stringify({
        theme: state.theme,
        editorFontSize: state.editorFontSize,
      })
    );
  });
}
