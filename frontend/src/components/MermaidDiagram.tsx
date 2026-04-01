"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import mermaid from "mermaid";
import { X, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

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
  const modalScrollRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (isStreaming || !containerRef.current) return;
    const renderId = `mermaid-${++_counter}`;
    setError(null);
    mermaid
      .render(renderId, chart)
      .then(({ svg: rendered }) => {
        if (containerRef.current) containerRef.current.innerHTML = rendered;
        setSvg(rendered);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [chart, isStreaming]);

  // Escape to close modal
  useEffect(() => {
    if (!modalOpen) return;
    setZoom(1);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setModalOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [modalOpen]);

  // Scroll-wheel zoom (non-passive so we can preventDefault)
  useEffect(() => {
    const el = modalScrollRef.current;
    if (!modalOpen || !el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return; // only zoom on Ctrl+scroll
      e.preventDefault();
      setZoom((z) => Math.min(4, Math.max(0.25, z - e.deltaY * 0.002)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [modalOpen]);

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
        <pre className="mt-1 text-[10px]" style={{ color: "#737373" }}>{chart}</pre>
      </div>
    );
  }

  return (
    <>
      {/* Thumbnail — click to open modal */}
      <div
        className="relative my-3 group cursor-zoom-in overflow-x-auto rounded-lg"
        style={{ background: "#0E0E0E", border: "1px solid #242424", padding: "1rem" }}
        onClick={() => svg && setModalOpen(true)}
      >
        <div ref={containerRef} />
        {svg && (
          <div
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded"
            style={{ background: "rgba(0,0,0,0.5)" }}
          >
            <Maximize2 size={13} style={{ color: "#737373" }} />
          </div>
        )}
      </div>

      {/* Modal */}
      {modalOpen && svg && createPortal(
        <div
          className="fixed inset-0 z-[300] flex items-center justify-center"
          onClick={() => setModalOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/80" />

          {/* Panel */}
          <div
            className="relative z-10 flex flex-col rounded-xl border shadow-2xl"
            style={{
              background: "#0E0E0E",
              borderColor: "#242424",
              width: "min(92vw, 1000px)",
              maxHeight: "90vh",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Toolbar */}
            <div
              className="flex items-center justify-between px-4 py-2 border-b flex-shrink-0"
              style={{ borderColor: "#1C1C1C" }}
            >
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}
                  className="p-1 rounded transition-colors text-[#737373] hover:text-[#F0F0F0]"
                >
                  <ZoomOut size={14} />
                </button>
                <span
                  className="text-[11px] tabular-nums w-10 text-center select-none"
                  style={{ color: "#737373" }}
                >
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
                  className="p-1 rounded transition-colors text-[#737373] hover:text-[#F0F0F0]"
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  onClick={() => setZoom(1)}
                  className="text-[10px] px-2 py-0.5 rounded border transition-colors"
                  style={{ borderColor: "#303030", color: "#737373" }}
                >
                  Reset
                </button>
                <span className="text-[10px] ml-2" style={{ color: "#404040" }}>
                  Ctrl+scroll to zoom
                </span>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded transition-colors text-[#737373] hover:text-[#F0F0F0]"
              >
                <X size={15} />
              </button>
            </div>

            {/* Scrollable diagram area */}
            <div
              ref={modalScrollRef}
              className="flex-1 overflow-auto p-8"
              style={{ minHeight: 0 }}
            >
              <div
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: "top center",
                  transition: "transform 0.15s ease",
                }}
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
