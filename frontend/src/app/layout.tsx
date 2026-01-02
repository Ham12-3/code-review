import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "AI Code Review",
  description: "AI-powered code review platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <Providers>
          <header className="border-b border-border px-6 py-4">
            <nav className="mx-auto flex max-w-7xl items-center justify-between">
              <a href="/" className="text-xl font-semibold">
                AI Code Review
              </a>
              <div className="flex items-center gap-4">
                <a
                  href="/reviews"
                  className="text-muted hover:text-foreground transition-colors"
                >
                  Reviews
                </a>
                <a
                  href="/github"
                  className="text-muted hover:text-foreground transition-colors"
                >
                  GitHub
                </a>
              </div>
            </nav>
          </header>
          <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
