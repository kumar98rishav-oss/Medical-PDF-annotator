import React from "react";
import { AlertTriangle, Check, Scissors, Trash2, X } from "lucide-react";

/**
 * Modal shown when a newly saved visit overlaps with existing ones.
 *
 * Props:
 *   newVisit      – the VisitResponse that was just saved
 *   warnings      – Array of { conflicting_visit_id, overlap_pages }
 *   allVisits     – full visits list (used to look up conflicting visit names)
 *   onKeepOverlap – () called when user wants pages in both sections
 *   onTrimPages   – (newStart, newEnd) called when user wants unique pages only
 *   onRemoveVisit – () called when user wants to delete this new visit
 *   onClose       – () called on backdrop click / dismiss (same as keep)
 */
export default function OverlapDialog({
  newVisit,
  warnings,
  allVisits,
  onKeepOverlap,
  onTrimPages,
  onRemoveVisit,
  onClose,
}) {
  if (!newVisit || !warnings || warnings.length === 0) return null;

  // Collect all overlapping page numbers across all conflicts
  const allOverlapPages = new Set(warnings.flatMap((w) => w.overlap_pages));

  // Compute the trimmed range: pages of the new visit minus all overlapping pages
  const newVisitPages = [];
  for (let p = newVisit.start_page; p <= newVisit.end_page; p++) {
    newVisitPages.push(p);
  }
  const uniquePages = newVisitPages.filter((p) => !allOverlapPages.has(p));

  // Find the largest contiguous block of unique pages
  let trimStart = null;
  let trimEnd = null;
  if (uniquePages.length > 0) {
    let bestStart = uniquePages[0];
    let bestEnd = uniquePages[0];
    let curStart = uniquePages[0];
    let curEnd = uniquePages[0];
    for (let i = 1; i < uniquePages.length; i++) {
      if (uniquePages[i] === curEnd + 1) {
        curEnd = uniquePages[i];
      } else {
        if (curEnd - curStart > bestEnd - bestStart) {
          bestStart = curStart;
          bestEnd = curEnd;
        }
        curStart = uniquePages[i];
        curEnd = uniquePages[i];
      }
    }
    if (curEnd - curStart >= bestEnd - bestStart) {
      bestStart = curStart;
      bestEnd = curEnd;
    }
    trimStart = bestStart;
    trimEnd = bestEnd;
  }

  const canTrim = trimStart !== null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 bg-amber-50 border-b border-amber-100">
          <div className="w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
          </div>
          <div className="flex-1">
            <h2 className="font-bold text-slate-800 text-sm">Page Overlap Detected</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              The pages you annotated conflict with existing visits.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-amber-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-3">
          {/* Conflict list */}
          <div className="space-y-2">
            {warnings.map((w) => {
              const conflicting = allVisits.find((v) => v.id === w.conflicting_visit_id);
              const label = conflicting
                ? `${conflicting.facility_name || "Unnamed visit"} ${conflicting.date_of_service ? `(${conflicting.date_of_service})` : ""}`.trim()
                : "another visit";
              const pages = w.overlap_pages;
              const pageLabel =
                pages.length === 1
                  ? `Page ${pages[0]}`
                  : pages.length <= 6
                  ? `Pages ${pages.join(", ")}`
                  : `Pages ${pages[0]}–${pages[pages.length - 1]} (${pages.length} pages)`;

              return (
                <div
                  key={w.conflicting_visit_id}
                  className="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-xl"
                >
                  <span className="text-amber-500 mt-0.5 flex-shrink-0 text-base leading-none">⚠</span>
                  <div className="text-xs text-slate-700 leading-relaxed">
                    <span className="font-semibold text-amber-800">{pageLabel}</span>{" "}
                    overlap with{" "}
                    <span className="font-semibold">{label}</span>.
                  </div>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-slate-500 font-medium">
            What would you like to do with the new visit (pages {newVisit.start_page}–{newVisit.end_page})?
          </p>
        </div>

        {/* Actions */}
        <div className="px-5 pb-5 space-y-2">
          {/* Keep Overlap */}
          <button
            onClick={onKeepOverlap}
            className="w-full flex items-center gap-3 px-4 py-3 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 hover:border-emerald-300 rounded-xl transition-all group"
          >
            <div className="w-7 h-7 rounded-full bg-emerald-100 group-hover:bg-emerald-200 flex items-center justify-center flex-shrink-0 transition-colors">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
            </div>
            <div className="text-left flex-1">
              <div className="text-sm font-semibold text-emerald-800">Keep Overlap</div>
              <div className="text-[11px] text-emerald-600 mt-0.5">
                Include overlapping pages in both visits during output.
              </div>
            </div>
          </button>

          {/* Trim to Unique Pages */}
          <button
            onClick={() => canTrim && onTrimPages(trimStart, trimEnd)}
            disabled={!canTrim}
            className="w-full flex items-center gap-3 px-4 py-3 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 rounded-xl transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <div className="w-7 h-7 rounded-full bg-blue-100 group-hover:bg-blue-200 flex items-center justify-center flex-shrink-0 transition-colors">
              <Scissors className="w-3.5 h-3.5 text-blue-600" />
            </div>
            <div className="text-left flex-1">
              <div className="text-sm font-semibold text-blue-800">
                Trim to Unique Pages
                {canTrim && (
                  <span className="ml-2 text-[11px] font-normal bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                    {trimStart === trimEnd ? `Page ${trimStart}` : `Pages ${trimStart}–${trimEnd}`}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-blue-600 mt-0.5">
                {canTrim
                  ? "Remove the overlapping pages from this visit's range."
                  : "No unique pages remain — use Remove Visit instead."}
              </div>
            </div>
          </button>

          {/* Remove Visit */}
          <button
            onClick={onRemoveVisit}
            className="w-full flex items-center gap-3 px-4 py-3 bg-red-50 hover:bg-red-100 border border-red-200 hover:border-red-300 rounded-xl transition-all group"
          >
            <div className="w-7 h-7 rounded-full bg-red-100 group-hover:bg-red-200 flex items-center justify-center flex-shrink-0 transition-colors">
              <Trash2 className="w-3.5 h-3.5 text-red-600" />
            </div>
            <div className="text-left flex-1">
              <div className="text-sm font-semibold text-red-800">Remove This Visit</div>
              <div className="text-[11px] text-red-500 mt-0.5">
                Delete this visit entirely.
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
