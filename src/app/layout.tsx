import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "The Delta Duo — Fantasy Football Lab",
  description:
    "Interactive data dashboard for The Delta Duo's fantasy football research: wide receivers, quarterbacks, and running backs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cabin+Sketch:wght@400;700&family=Caveat:wght@500;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        <Nav />
        <main className="mx-auto max-w-6xl px-4 pb-24 pt-6 sm:px-6">{children}</main>
        <footer
          className="mx-auto flex max-w-6xl flex-wrap items-baseline justify-between gap-2 px-6 pb-10 text-xs"
          style={{ color: "var(--ink-faint)" }}
        >
          <span>
            © {new Date().getFullYear()} The Delta Duo · All numbers from original Delta Duo research ·{" "}
            <a href="https://getinsidethelab.com" className="underline" target="_blank" rel="noreferrer">
              getinsidethelab.com
            </a>
          </span>
          <span className="chalk-annotation" style={{ fontSize: "1.05rem" }}>
            we don&apos;t draft players. we draft deltas.
          </span>
        </footer>
      </body>
    </html>
  );
}
