import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Federal Tax Intelligence System",
  description: "Official Tax Intelligence and Audit Platform",
};

import ChatWidget from "@/components/ChatWidget";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans flex flex-col h-screen overflow-hidden bg-slate-50`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
