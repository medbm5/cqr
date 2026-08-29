import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Sidebar } from "@/components/shell/sidebar";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "Citalid Risk Engine",
  description:
    "Annualized cyber loss of the target company, traceable from telemetry to euros.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-dvh font-sans">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-navy-800 focus:px-4 focus:py-2 focus:text-sm focus:text-ink"
        >
          Skip to content
        </a>

        <div className="lg:flex">
          <Sidebar />
          <main id="content" className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-10 lg:py-12">
            <div className="mx-auto max-w-6xl">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
