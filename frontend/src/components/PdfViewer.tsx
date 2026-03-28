"use client";

import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, Loader2, FileText } from "lucide-react";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface PdfViewerProps {
  url: string;
  goToPage?: number;
}

export default function PdfViewer({ url, goToPage }: PdfViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [pageNum, setPageNum] = useState(1);
  const [pdfWidth, setPdfWidth] = useState(600);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setPdfWidth(entry.contentRect.width - 16);
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (goToPage && goToPage >= 1 && goToPage <= numPages) {
      setPageNum(goToPage);
    }
  }, [goToPage, numPages]);

  const navigate = (p: number) => {
    if (p >= 1 && p <= numPages) setPageNum(p);
  };

  return (
    <div ref={containerRef} className="flex flex-col min-h-0 h-full">
      <div className="flex items-center justify-center gap-3 py-2 border-b border-border bg-bg-card/50 shrink-0">
        <button onClick={() => navigate(pageNum - 1)} disabled={pageNum <= 1} className="p-1 rounded hover:bg-bg-hover disabled:opacity-30 transition-colors">
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm text-text-muted tabular-nums">
          <input
            type="number"
            min={1}
            max={numPages}
            value={pageNum}
            onChange={(e) => navigate(parseInt(e.target.value) || 1)}
            className="w-12 text-center bg-bg-input border border-border rounded px-1 py-0.5 text-sm text-text"
          />
          <span className="ml-1">/ {numPages || "..."}</span>
        </span>
        <button onClick={() => navigate(pageNum + 1)} disabled={pageNum >= numPages} className="p-1 rounded hover:bg-bg-hover disabled:opacity-30 transition-colors">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-2 flex justify-center">
        <Document
          file={url}
          onLoadSuccess={({ numPages: n }) => setNumPages(n)}
          loading={
            <div className="flex flex-col items-center justify-center py-20 text-text-muted">
              <Loader2 className="w-6 h-6 animate-spin mb-2" />
              <span className="text-sm">Loading PDF...</span>
            </div>
          }
          error={
            <div className="flex flex-col items-center justify-center py-20 text-text-muted">
              <FileText className="w-8 h-8 mb-2" />
              <span className="text-sm">Could not load PDF.</span>
            </div>
          }
        >
          <Page pageNumber={pageNum} width={pdfWidth > 100 ? pdfWidth : 500} />
        </Document>
      </div>
    </div>
  );
}
