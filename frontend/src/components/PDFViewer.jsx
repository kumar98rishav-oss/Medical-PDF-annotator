import React, { useState, useRef, useEffect, useCallback } from "react";
import { pageImageURL } from "../api";

const ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0];

export default function PDFViewer({
  pdfId,
  currentPage,
  totalPages,
  zoom,
  onPageChange,
  onZoomChange,
}) {
  // displayedSrc  — the image actually rendered in the DOM right now
  // displayedZoom — the zoom level that image was built for
  const [displayedSrc, setDisplayedSrc] = useState(null);
  const [displayedZoom, setDisplayedZoom] = useState(zoom);
  const [imgLoading, setImgLoading] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const scrollContainerRef = useRef(null);
  const loaderRef = useRef(null);

  // track whether the CURRENT load is a page-change vs zoom-change
  // so we know whether to blank the viewer or keep the scaled image
  const loadingPageRef = useRef(currentPage);
  const loadingPdfRef = useRef(pdfId);

  // ── Draggable floating nav ──
  const [navY, setNavY] = useState(null);
  const dragging = useRef(false);
  const dragStartY = useRef(0);
  const dragStartNavY = useRef(0);
  const navRef = useRef(null);

  // Scroll to top on page change
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: 0, behavior: "instant" });
    }
  }, [currentPage]);

  // ── Main image loader ──
  // Runs whenever page, zoom, pdf, or retry changes.
  // Shows the previous image (CSS-scaled) while loading a zoom change,
  // but shows the spinner while loading a page / pdf change.
  useEffect(() => {
    if (!pdfId || !totalPages) return;

    const targetSrc = pageImageURL(pdfId, currentPage, zoom);
    const isPageChange = currentPage !== loadingPageRef.current || pdfId !== loadingPdfRef.current;
    loadingPageRef.current = currentPage;
    loadingPdfRef.current = pdfId;

    // Cancel any previous in-flight load
    if (loaderRef.current) {
      loaderRef.current.onload = null;
      loaderRef.current.onerror = null;
      loaderRef.current.src = "";
    }

    setImgLoading(true);
    setImgError(false);

    // Page change → blank immediately so stale page never shows
    if (isPageChange) {
      setDisplayedSrc(null);
      setDisplayedZoom(zoom);
    }

    const img = new Image();
    loaderRef.current = img;

    img.onload = () => {
      setDisplayedSrc(targetSrc);
      setDisplayedZoom(zoom);
      setImgLoading(false);
    };
    img.onerror = () => {
      setImgLoading(false);
      setImgError(true);
    };
    img.src = targetSrc;

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdfId, currentPage, zoom, totalPages, retryCount]);

  // ── Preload adjacent pages so navigation is instant ──
  useEffect(() => {
    if (!pdfId || !totalPages) return;
    [currentPage + 1, currentPage + 2, currentPage - 1].forEach((p) => {
      if (p >= 1 && p <= totalPages) {
        const pre = new Image();
        pre.src = pageImageURL(pdfId, p, zoom);
      }
    });
  }, [pdfId, currentPage, zoom, totalPages]);

  // ── Drag handlers ──
  const onDragStart = useCallback((e) => {
    e.preventDefault();
    dragging.current = true;
    dragStartY.current = e.clientY;
    const container = scrollContainerRef.current;
    if (container && navRef.current) {
      const containerRect = container.getBoundingClientRect();
      const navRect = navRef.current.getBoundingClientRect();
      dragStartNavY.current = navRect.top - containerRect.top;
    }
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current) return;
      const container = scrollContainerRef.current;
      if (!container) return;
      const containerRect = container.getBoundingClientRect();
      const delta = e.clientY - dragStartY.current;
      let newY = dragStartNavY.current + delta;
      const navHeight = navRef.current ? navRef.current.offsetHeight : 100;
      newY = Math.max(0, Math.min(containerRect.height - navHeight, newY));
      setNavY(newY);
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  if (!pdfId || !totalPages) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        No PDF loaded
      </div>
    );
  }

  const goTo = (page) => {
    const clamped = Math.max(1, Math.min(totalPages, page));
    onPageChange(clamped);
  };

  const zoomIn = () => {
    const idx = ZOOM_LEVELS.indexOf(zoom);
    if (idx < ZOOM_LEVELS.length - 1) onZoomChange(ZOOM_LEVELS[idx + 1]);
  };

  const zoomOut = () => {
    const idx = ZOOM_LEVELS.indexOf(zoom);
    if (idx > 0) onZoomChange(ZOOM_LEVELS[idx - 1]);
  };

  // CSS zoom for instant visual feedback while the server responds to a zoom change.
  // displayedZoom is the zoom level of the currently shown image;
  // dividing gives the scale needed to make it LOOK like the requested zoom.
  const cssZoom = displayedSrc && displayedZoom > 0 ? zoom / displayedZoom : 1;

  return (
    <>
      {/* ── Toolbar ── */}
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between flex-shrink-0">
        {/* Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => goTo(1)}
            disabled={currentPage <= 1}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            title="First page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={() => goTo(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            title="Previous page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="flex items-center gap-1 text-sm">
            <span className="text-gray-500">Page</span>
            <input
              type="number"
              min={1}
              max={totalPages}
              value={currentPage}
              onChange={(e) => goTo(parseInt(e.target.value) || 1)}
              className="w-14 text-center border border-gray-300 rounded px-1 py-0.5 text-sm"
            />
            <span className="text-gray-500">of {totalPages}</span>
          </div>

          <button
            onClick={() => goTo(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            title="Next page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          <button
            onClick={() => goTo(totalPages)}
            disabled={currentPage >= totalPages}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            title="Last page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-2">
          <button
            onClick={zoomOut}
            disabled={zoom <= ZOOM_LEVELS[0]}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
            title="Zoom out"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
            </svg>
          </button>
          <span className="text-xs text-gray-500 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={zoomIn}
            disabled={zoom >= ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
            title="Zoom in"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Page Image ── */}
      <div className="flex-1 overflow-auto flex justify-center p-4 relative" ref={scrollContainerRef}>
        <div className="relative">

          {/* Full spinner: only when there is NO image to show (page change / first load) */}
          {imgLoading && !displayedSrc && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10 min-h-[400px] min-w-[300px]">
              <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* Small corner spinner: zoom is loading but current page is still visible */}
          {imgLoading && displayedSrc && (
            <div className="absolute top-2 right-2 z-10 bg-white/90 rounded-full p-1.5 shadow border border-slate-100">
              <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {imgError ? (
            <div className="flex items-center justify-center h-96 text-gray-400">
              <div className="text-center">
                <p className="text-lg">Failed to load page {currentPage}</p>
                <button
                  onClick={() => {
                    setImgError(false);
                    setRetryCount((c) => c + 1);
                  }}
                  className="mt-2 text-blue-500 underline text-sm"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : displayedSrc ? (
            <img
              src={displayedSrc}
              alt={`Page ${currentPage}`}
              className="page-image"
              style={cssZoom !== 1 ? { zoom: cssZoom } : undefined}
            />
          ) : null}
        </div>

        {/* ── Floating Page Up/Down Arrows (right side, draggable) ── */}
        <div
          ref={navRef}
          className="page-nav-floating"
          style={navY !== null ? { top: `${navY}px`, transform: "none" } : {}}
        >
          <button
            onClick={() => goTo(currentPage - 1)}
            disabled={currentPage <= 1}
            className="page-nav-arrow"
            title="Previous page"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <span
            className="page-nav-label page-nav-drag-handle"
            onMouseDown={onDragStart}
            title="Drag to reposition"
          >
            {currentPage}
          </span>
          <button
            onClick={() => goTo(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="page-nav-arrow"
            title="Next page"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
