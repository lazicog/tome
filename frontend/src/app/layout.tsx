import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "Tome",
  description: "AI-powered learning companion for technical books.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable}`}>
      <body className="bg-background text-foreground min-h-screen antialiased">
        <div
          aria-hidden="true"
          style={{ position: "fixed", top: 0, left: 0, right: 0, height: "1px", background: "rgba(107,155,107,0.35)", zIndex: 9999, pointerEvents: "none" }}
        />
        {children}
      </body>
    </html>
  );
}
