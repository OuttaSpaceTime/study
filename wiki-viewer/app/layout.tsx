import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "highlight.js/styles/atom-one-light.css";
import { WikiDataProvider } from "@/components/providers/WikiDataProvider";
import Sidebar from "@/components/sidebar/Sidebar";
import GraphRail from "@/components/graph/GraphRail";
import CommandPalette from "@/components/search/CommandPalette";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Study Wiki",
  description: "Local viewer for the study wiki",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-screen overflow-hidden font-sans">
        <WikiDataProvider>
          <div className="flex h-full">
            <Sidebar />
            <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
            <GraphRail />
          </div>
          <CommandPalette />
        </WikiDataProvider>
      </body>
    </html>
  );
}
