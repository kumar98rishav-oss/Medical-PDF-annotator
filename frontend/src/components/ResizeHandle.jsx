import React, { useCallback, useRef, useEffect } from "react";

/**
 * Vertical drag handle between two panels.
 * Fires onResize(deltaX) while dragging.
 */
export default function ResizeHandle({ onResize, className = "" }) {
  const dragging = useRef(false);
  const startX = useRef(0);

  const onMouseDown = useCallback((e) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      startX.current = e.clientX;
      onResize(delta);
    };

    const onMouseUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onResize]);

  return (
    <div
      onMouseDown={onMouseDown}
      className={`group flex-shrink-0 w-[5px] cursor-col-resize relative z-20 
        hover:bg-primary-400/40 active:bg-primary-500/50 transition-colors duration-150
        ${className}`}
      title="Drag to resize"
    >
      {/* Visual grip dots */}
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 flex flex-col items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="w-1 h-1 rounded-full bg-slate-400" />
        <span className="w-1 h-1 rounded-full bg-slate-400" />
        <span className="w-1 h-1 rounded-full bg-slate-400" />
      </div>
    </div>
  );
}
