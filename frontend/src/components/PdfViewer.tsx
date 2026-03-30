"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/TextLayer.css";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2, AlertCircle } from "lucide-react";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PdfViewerProps {
  url: string;
  title?: string;
  goToPage?: number;
  onPageChange?: (page: number) => void;
  onNumPagesChange?: (n: number) => void;
}

export default function PdfViewer({ url, title, goToPage, onPageChange, onNumPagesChange }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageNum, setPageNum] = useState(1);
  const [inputVal, setInputVal] = useState("1");
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [containerWidth, setContainerWidth] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<(HTMLDivElement | null)[]>([]);
  const prevGoToPage = useRef<number | undefined>(undefined);
  const pageNumRef = useRef(1);
  const numPagesRef = useRef(0);
  const resizeDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Fit-to-width via ResizeObserver — debounced so pages only re-render
     once after a panel-width transition completes, not on every frame */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? 0;
      if (resizeDebounce.current) clearTimeout(resizeDebounce.current);
      resizeDebounce.current = setTimeout(() => setContainerWidth(width), 320);
    });
    obs.observe(el);
    return () => { obs.disconnect(); if (resizeDebounce.current) clearTimeout(resizeDebounce.current); };
  }, []);

  const pageWidth = containerWidth > 0 ? (containerWidth - 32) * zoomLevel : undefined;

  /* Scroll to a page element — instant, no CSS smooth (avoids clashing with rAF loop) */
  const scrollToPage = useCallback((n: number) => {
    const el = pageRefs.current[n - 1];
    const container = scrollRef.current;
    if (!el || !container) return;
    container.scrollTop = el.offsetTop - 16;
  }, []);

  /* IntersectionObserver — track which page is most visible */
  useEffect(() => {
    if (numPages === 0) return;
    const ratios = new Map<number, number>();

    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const page = parseInt(entry.target.getAttribute("data-page") ?? "1", 10);
          ratios.set(page, entry.intersectionRatio);
        }
        let best = { page: 1, ratio: 0 };
        ratios.forEach((ratio, page) => {
          if (ratio > best.ratio) best = { page, ratio };
        });
        if (best.ratio > 0) {
          pageNumRef.current = best.page;
          setPageNum(best.page);
          setInputVal(String(best.page));
          onPageChange?.(best.page);
        }
      },
      {
        root: scrollRef.current,
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );

    pageRefs.current.forEach((ref) => ref && obs.observe(ref));
    return () => obs.disconnect();
  }, [numPages, onPageChange]);

  /* goToPage prop */
  useEffect(() => {
    if (goToPage !== undefined && goToPage !== prevGoToPage.current) {
      prevGoToPage.current = goToPage;
      scrollToPage(goToPage);
    }
  }, [goToPage, scrollToPage]);

  /* Keyboard navigation — registered once, uses refs to avoid re-mounting */
  useEffect(() => {
    const keysHeld = new Set<string>();
    let rafId: number | null = null;

    const tick = () => {
      const scroll = scrollRef.current;
      if (scroll && (keysHeld.has("ArrowUp") || keysHeld.has("ArrowDown"))) {
        scroll.scrollTop += keysHeld.has("ArrowDown") ? 20 : -20;
        rafId = requestAnimationFrame(tick);
      } else {
        rafId = null;
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        keysHeld.add(e.key);
        if (!rafId) rafId = requestAnimationFrame(tick);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        scrollToPage(Math.max(1, pageNumRef.current - 1));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        scrollToPage(Math.min(numPagesRef.current || 1, pageNumRef.current + 1));
      }
    };

    const onKeyUp = (e: KeyboardEvent) => keysHeld.delete(e.key);

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [scrollToPage]); // scrollToPage is stable (useCallback) — this runs once

  const handleInputCommit = () => {
    const n = parseInt(inputVal, 10);
    const clamped = Math.max(1, Math.min(isNaN(n) ? pageNum : n, numPages || 1));
    setInputVal(String(clamped));
    scrollToPage(clamped);
  };

  return (
    <div ref={containerRef} className="flex flex-col h-full" style={{ background: "#0E0E0E" }}>

      {/* ── Document header ── */}
      {(title || numPages > 0) && (
        <div
          className="flex items-center justify-between px-4 h-8 flex-shrink-0 border-b"
          style={{ background: "#111111", borderColor: "#1C1C1C" }}
        >
          <span className="text-[11px] truncate" style={{ color: "#404040" }}>
            {title ?? ""}
          </span>
          {numPages > 0 && (
            <span className="text-[11px] flex-shrink-0 ml-2 tabular-nums" style={{ color: "#303030" }}>
              {pageNum} / {numPages}
            </span>
          )}
        </div>
      )}

      {/* ── Scrollable pages ── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4">
        <Document
          file={url}
          onLoadSuccess={({ numPages }) => {
            setNumPages(numPages);
            numPagesRef.current = numPages;
            pageRefs.current = new Array(numPages).fill(null);
            onNumPagesChange?.(numPages);
          }}
          loading={
            <div className="flex flex-col items-center justify-center mt-24 gap-3">
              <Loader2 size={20} className="animate-spin" style={{ color: "#737373" }} />
              <span className="text-xs" style={{ color: "#737373" }}>Loading PDF…</span>
            </div>
          }
          error={
            <div className="flex flex-col items-center justify-center mt-24 gap-3">
              <AlertCircle size={20} style={{ color: "#EF4444" }} />
              <div className="text-center">
                <p className="text-sm font-medium" style={{ color: "#F0F0F0" }}>Failed to load PDF</p>
                <p className="text-xs mt-1" style={{ color: "#737373" }}>Try re-uploading the file or refreshing the page</p>
              </div>
            </div>
          }
        >
          {Array.from({ length: numPages }, (_, i) => (
            <div
              key={i + 1}
              ref={(el) => { pageRefs.current[i] = el; }}
              data-page={i + 1}
              className="flex justify-center mb-3"
            >
              <Page
                pageNumber={i + 1}
                width={pageWidth}
                renderTextLayer
                renderAnnotationLayer
              />
            </div>
          ))}
        </Document>
      </div>

      {/* ── Bottom toolbar ── */}
      <div
        className="flex items-center justify-center gap-3 h-10 px-4 flex-shrink-0 border-t"
        style={{ background: "#0E0E0E", borderColor: "#242424" }}
      >
        {/* Prev */}
        <button
          onClick={() => scrollToPage(Math.max(1, pageNum - 1))}
          disabled={pageNum <= 1}
          className="p-1 rounded transition-colors disabled:opacity-30 text-[#737373] hover:text-[#F0F0F0]"
        >
          <ChevronLeft size={14} />
        </button>

        {/* Page input / total */}
        <div className="flex items-center gap-1.5">
          <input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleInputCommit(); }}
            onBlur={handleInputCommit}
            className="w-10 h-6 text-center rounded border text-xs outline-none transition-colors"
            style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(99,102,241,0.5)")}
          />
          <span className="text-xs" style={{ color: "#737373" }}>/ {numPages || "—"}</span>
        </div>

        {/* Next */}
        <button
          onClick={() => scrollToPage(Math.min(numPages || 1, pageNum + 1))}
          disabled={pageNum >= numPages}
          className="p-1 rounded transition-colors disabled:opacity-30 text-[#737373] hover:text-[#F0F0F0]"
        >
          <ChevronRight size={14} />
        </button>

        {/* Divider */}
        <div className="w-px h-4 mx-1" style={{ background: "#242424" }} />

        {/* Zoom out */}
        <button
          onClick={() => setZoomLevel((z) => Math.max(0.5, +(z - 0.15).toFixed(2)))}
          className="p-1 rounded transition-colors text-[#737373] hover:text-[#F0F0F0]"
          title="Zoom out"
        >
          <ZoomOut size={13} />
        </button>

        <span className="text-xs w-9 text-center select-none" style={{ color: "#737373" }}>
          {Math.round(zoomLevel * 100)}%
        </span>

        {/* Zoom in */}
        <button
          onClick={() => setZoomLevel((z) => Math.min(3.0, +(z + 0.15).toFixed(2)))}
          className="p-1 rounded transition-colors text-[#737373] hover:text-[#F0F0F0]"
          title="Zoom in"
        >
          <ZoomIn size={13} />
        </button>
      </div>
    </div>
  );
}
