"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PdfViewerProps {
  url: string;
  goToPage?: number;
}

export default function PdfViewer({ url, goToPage }: PdfViewerProps) {
  const [pageNum, setPageNum] = useState(1);
  const [inputVal, setInputVal] = useState("1");
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const prevSrc = useRef("");

  useEffect(() => {
    if (goToPage && goToPage >= 1 && goToPage !== pageNum) {
      setPageNum(goToPage);
      setInputVal(String(goToPage));
    }
  }, [goToPage]);

  const iframeSrc = `${url}?p=${pageNum}#page=${pageNum}&toolbar=0&navpanes=0`;

  useEffect(() => {
    if (!iframeRef.current || iframeSrc === prevSrc.current) return;
    prevSrc.current = iframeSrc;
    iframeRef.current.src = iframeSrc;
  }, [iframeSrc]);

  const navigate = (p: number) => {
    if (p >= 1) {
      setPageNum(p);
      setInputVal(String(p));
    }
  };

  return (
    <div className="flex flex-col min-h-0 h-full">
      <div className="flex items-center justify-center gap-3 py-2 border-b border-border bg-bg-card/50 shrink-0">
        <button
          onClick={() => navigate(pageNum - 1)}
          disabled={pageNum <= 1}
          className="p-1 rounded hover:bg-bg-hover disabled:opacity-30 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm text-text-muted tabular-nums">
          Page{" "}
          <input
            type="number"
            min={1}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onBlur={() => {
              const p = parseInt(inputVal);
              if (p >= 1) navigate(p);
              else setInputVal(String(pageNum));
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const p = parseInt(inputVal);
                if (p >= 1) navigate(p);
                else setInputVal(String(pageNum));
              }
            }}
            className="w-14 text-center bg-bg-input border border-border rounded px-1 py-0.5 text-sm text-text"
          />
        </span>
        <button
          onClick={() => navigate(pageNum + 1)}
          className="p-1 rounded hover:bg-bg-hover transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 relative">
        <iframe
          ref={iframeRef}
          src={`${url}?p=1#page=1&toolbar=0&navpanes=0`}
          className="w-full h-full border-0"
          title="PDF Viewer"
        />
      </div>
    </div>
  );
}
