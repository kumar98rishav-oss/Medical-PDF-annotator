import React, { useRef, useEffect } from "react";

export default function PageSidebar({
  pageCount,
  currentPage,
  markedPages,       // Map<pageNum, color>
  onPageClick,
}) {
  const containerRef = useRef(null);
  const activeRef = useRef(null);

  // Auto-scroll to keep current page visible
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ block: "nearest" });
    }
  }, [currentPage]);

  if (!pageCount) return null;

  const pages = Array.from({ length: pageCount }, (_, i) => i + 1);

  return (
    <div
      ref={containerRef}
      className="w-[80px] bg-slate-50 border-r border-slate-200 overflow-y-auto flex-shrink-0 hide-scrollbar"
    >
      <div className="p-2 space-y-1">
        {pages.map((num) => {
          const isCurrent = num === currentPage;
          const color = markedPages.get(num);
          const isMarked = !!color;

          return (
            <button
              key={num}
              ref={isCurrent ? activeRef : null}
              onClick={() => onPageClick(num)}
              className={`w-full flex items-center justify-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                isCurrent
                  ? "bg-primary-100 text-primary-800 font-bold shadow-sm"
                  : "hover:bg-slate-200 text-slate-600 hover:text-slate-900"
              }`}
              title={`Page ${num}${isMarked ? " (annotated)" : ""}`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0 shadow-sm"
                style={{
                  backgroundColor: isMarked ? color : "transparent",
                  border: isMarked ? "none" : "1.5px solid #cbd5e1",
                }}
              />
              <span className="tabular-nums">{num}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}