"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    darkMode: true,
    background: "#151515",
    primaryColor: "rgba(107,155,107,0.18)",
    primaryTextColor: "#F0F0F0",
    primaryBorderColor: "#303030",
    lineColor: "#6B9B6B",
    secondaryColor: "#1C1C1C",
    tertiaryColor: "#0E0E0E",
    edgeLabelBackground: "#151515",
    nodeTextColor: "#F0F0F0",
  },
});

let _counter = 0;

export default function MermaidDiagram({
  chart,
  isStreaming = false,
}: {
  chart: string;
  isStreaming?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`mermaid-${++_counter}`);

  useEffect(() => {
    if (isStreaming || !containerRef.current) return;
    setError(null);
    mermaid
      .render(idRef.current, chart)
      .then(({ svg }) => {
        if (containerRef.current) containerRef.current.innerHTML = svg;
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [chart, isStreaming]);

  if (isStreaming) {
    return (
      <div
        className="my-3 rounded-lg flex items-center gap-2 px-4 py-3"
        style={{ background: "#0E0E0E", border: "1px solid #242424", color: "#404040" }}
      >
        <span className="text-xs">Generating diagram…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="my-2 rounded-lg border px-3 py-2 text-xs font-mono overflow-x-auto"
        style={{ background: "#0E0E0E", borderColor: "#303030" }}
      >
        <span style={{ color: "#EF4444" }}>Diagram render error: </span>
        {error}
        <pre className="mt-1 text-[10px]" style={{ color: "#737373" }}>
          {chart}
        </pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-3 overflow-x-auto rounded-lg"
      style={{ background: "#0E0E0E", border: "1px solid #242424", padding: "1rem" }}
    />
  );
}
