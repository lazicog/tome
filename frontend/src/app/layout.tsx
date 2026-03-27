import type { ReactNode } from "react";

export const metadata = {
  title: "Tome",
  description: "AI-powered learning companion for technical books."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Arial, sans-serif", background: "#0b1020", color: "#e2e8f0" }}>
        <main style={{ maxWidth: 1000, margin: "0 auto", padding: "2rem 1rem" }}>{children}</main>
      </body>
    </html>
  );
}
