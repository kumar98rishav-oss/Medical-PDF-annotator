import React, { useState, useRef, useEffect } from "react";
import { Zap, CheckCircle, ChevronDown, FileBox, FileArchive, Download, RefreshCw, Loader2 } from "lucide-react";
import * as api from "../api";

export default function ProcessDropdown({ pdfId, pdfInfo, visitCount }) {
  const [open, setOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState("combined");
  const [progress, setProgress] = useState(null);
  const dropdownRef = useRef(null);
  const pollRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const pollJobStatus = (jobId) => {
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getProcessStatus(jobId);
        setProgress(status.progress);

        if (status.status === "complete") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setProcessing(false);
          setResult({ id: jobId, download_url: status.download_url, ...status });
        } else if (status.status === "error") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setProcessing(false);
          setError(status.error_message || "Processing failed");
        }
      } catch (e) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setProcessing(false);
        setError(e.message);
      }
    }, 1500);
  };

  const handleProcess = async () => {
    setProcessing(true);
    setError(null);
    setResult(null);
    setProgress(null);
    try {
      const res = await api.processPDF(pdfId, mode);
      // Async: res has job_id and status="queued"
      if (res.job_id) {
        pollJobStatus(res.job_id);
      } else if (res.id) {
        // Fallback if endpoint returns sync result
        setResult(res);
        setProcessing(false);
      }
    } catch (e) {
      setError(e.message);
      setProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const url = result.download_url
      ? (result.download_url.startsWith("/") ? result.download_url : `/api${result.download_url}`)
      : api.downloadURL(result.id);
    window.open(url, "_blank");
  };

  if (!pdfId) return null;

  const markedPct = pdfInfo
    ? Math.round((pdfInfo.marked_pages / pdfInfo.page_count) * 100)
    : 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 ${
          result
            ? "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30"
            : "bg-primary-500/20 text-primary-300 hover:bg-primary-500/30 border border-primary-500/30"
        }`}
      >
        {result ? <CheckCircle className="w-3.5 h-3.5" /> : <Zap className="w-3.5 h-3.5" />}
        <span className="hidden sm:inline">
          {result ? "Download" : "Process"}
        </span>
        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 overflow-hidden">
          {/* Stats bar */}
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-100">
            <div className="flex justify-between text-[11px] font-medium text-slate-500 mb-1.5">
              <span>{visitCount} visit{visitCount !== 1 ? "s" : ""}</span>
              <span>
                {pdfInfo?.marked_pages || 0}/{pdfInfo?.page_count || 0} pages ({markedPct}%)
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-primary-400 to-primary-600 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${markedPct}%` }}
              />
            </div>
          </div>

          <div className="p-4 space-y-3">
            {/* Output mode toggle */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Output:</span>
              <div className="flex bg-slate-100 rounded-lg p-0.5 flex-1">
                <button
                  type="button"
                  onClick={() => setMode("combined")}
                  className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all ${
                    mode === "combined"
                      ? "bg-white text-primary-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <FileBox className="inline w-3 h-3 mr-1" /> Combined PDF
                </button>
                <button
                  type="button"
                  onClick={() => setMode("split")}
                  className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all ${
                    mode === "split"
                      ? "bg-white text-primary-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <FileArchive className="inline w-3 h-3 mr-1" /> Split ZIP
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="text-xs text-red-700 font-medium bg-red-50 border border-red-200 p-2.5 rounded-lg">
                {error}
              </div>
            )}

            {/* Progress indicator */}
            {processing && progress && (
              <div className="text-xs bg-blue-50 border border-blue-200 rounded-lg p-2.5 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                <span className="font-semibold text-blue-700">Processing visits: {progress}</span>
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="text-xs bg-emerald-50 border border-emerald-200 rounded-lg p-3 space-y-1">
                <p className="font-semibold text-emerald-800 flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Processing complete!
                </p>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleProcess}
                disabled={processing || visitCount === 0}
                className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 text-white py-2 rounded-lg text-xs font-bold hover:from-primary-700 hover:to-primary-800 active:scale-[0.98] transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? (
                  <span className="flex items-center justify-center gap-1.5">
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Processing...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-1 uppercase tracking-wide">
                    <RefreshCw className="w-3.5 h-3.5" /> Process PDF
                  </span>
                )}
              </button>

              {result && (
                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-bold uppercase tracking-wide hover:bg-slate-900 active:scale-[0.97] transition-all shadow-md"
                >
                  <Download className="inline w-3.5 h-3.5 mr-1" /> Download
                </button>
              )}
            </div>

            {visitCount === 0 && (
              <p className="text-[10px] text-slate-400 text-center font-medium">
                Add at least one visit to process
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
