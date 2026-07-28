import React, { useState } from "react";
import * as api from "../api";

export default function ProcessPanel({ pdfId, pdfInfo, visitCount }) {
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState("combined"); // "combined" | "split"

  const handleProcess = async () => {
    setProcessing(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.processPDF(pdfId, mode);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    window.open(api.downloadURL(result.id), "_blank");
  };

  if (!pdfId) return null;

  const markedPct = pdfInfo
    ? Math.round((pdfInfo.marked_pages / pdfInfo.page_count) * 100)
    : 0;

  return (
    <div className="border-t border-slate-200 p-5 bg-slate-50/80 space-y-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.04)] z-10 relative">
      {/* Stats */}
      <div className="flex justify-between text-xs font-medium text-slate-500">
        <span>{visitCount} visit{visitCount !== 1 ? "s" : ""} annotated</span>
        <span>
          {pdfInfo?.marked_pages || 0} / {pdfInfo?.page_count || 0} pages ({markedPct}%)
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-primary-400 to-primary-600 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${markedPct}%` }}
        />
      </div>

      {/* Output Mode Toggle */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Output:</span>
        <div className="flex bg-slate-200/80 rounded-lg p-0.5 flex-1">
          <button
            type="button"
            onClick={() => setMode("combined")}
            className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all duration-200 ${
              mode === "combined"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            📄 Combined PDF
          </button>
          <button
            type="button"
            onClick={() => setMode("split")}
            className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all duration-200 ${
              mode === "split"
                ? "bg-white text-primary-700 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            📦 Split ZIP
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-xs text-red-700 font-medium bg-red-50 border border-red-200 p-3 rounded-xl">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="text-xs bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-1.5 shadow-sm">
          <p className="font-semibold text-emerald-800 flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            Processing complete!
          </p>
          <div className="text-emerald-700 text-[11px]">
            {result.page_count} pg • {result.visit_count} visits • {result.facilities.join(", ")}
          </div>
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleProcess}
          disabled={processing || visitCount === 0}
          className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 text-white py-2.5 rounded-xl text-sm font-bold hover:from-primary-700 hover:to-primary-800 active:scale-[0.98] transition-all duration-200 shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {processing ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-1.5 uppercase tracking-wide">
              🔄 Process PDF
            </span>
          )}
        </button>

        {result && (
          <button
            onClick={handleDownload}
            className="px-5 py-2.5 bg-slate-800 text-white rounded-xl text-sm font-bold uppercase tracking-wide hover:bg-slate-900 active:scale-[0.97] transition-all shadow-md"
          >
            📥 Download
          </button>
        )}
      </div>

      {visitCount === 0 && (
        <p className="text-[10px] text-slate-400 text-center font-medium uppercase tracking-wider">
          Add at least one visit to process
        </p>
      )}
    </div>
  );
}