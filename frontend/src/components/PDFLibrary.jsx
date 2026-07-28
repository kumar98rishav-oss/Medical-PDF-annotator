import React, { useEffect, useState } from "react";
import { FileText, Trash2 } from "lucide-react";
import * as api from "../api";

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  });
}

export default function PDFLibrary({ onSelect, activeId }) {
  const [pdfs, setPdfs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const list = await api.listPDFs();
      setPdfs(list);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [activeId]); // Refresh list if activeId changes (or simply let parent trigger refresh, but this is okay)

  const handleDelete = async (e, pdfId) => {
    e.stopPropagation();
    if (!confirm("Delete this PDF and all its annotations?")) return;
    try {
      await api.deletePDF(pdfId);
      setPdfs((prev) => prev.filter((p) => p.id !== pdfId));
    } catch (err) {
      alert("Failed to delete: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-3 p-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse bg-slate-100 h-16 rounded-xl w-full"></div>
        ))}
      </div>
    );
  }

  if (pdfs.length === 0) {
    return (
      <div className="text-center py-8 px-4 text-slate-400">
        <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm font-medium">No documents</p>
        <p className="text-xs mt-1">Upload a PDF to begin</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-2 mb-2">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Library
        </h3>
        <span className="text-xs font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {pdfs.length}
        </span>
      </div>
      
      <div className="overflow-y-auto pr-1 space-y-2 hide-scrollbar">
        {pdfs.map((pdf) => {
          const isActive = pdf.id === activeId;
          return (
            <div
              key={pdf.id}
              onClick={() => onSelect(pdf.id)}
              className={`group relative flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all duration-200 border ${
                isActive 
                  ? "bg-brand-dark text-white border-brand-dark shadow-md" 
                  : "bg-white border-slate-200 hover:border-brand-light hover:shadow-soft text-slate-700"
              }`}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div className={`p-2 rounded-lg flex-shrink-0 transition-colors ${isActive ? "bg-white/20 text-white" : "bg-slate-50 text-brand-light group-hover:bg-brand-light/10"}`}>
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-semibold truncate ${isActive ? "text-white" : "text-slate-800"}`}>
                    {pdf.filename}
                  </p>
                  <p className={`text-xs mt-0.5 mt-1 font-medium ${isActive ? "text-blue-200" : "text-slate-500"}`}>
                    {formatDate(pdf.uploaded_at)} • {formatBytes(pdf.file_size)}
                  </p>
                </div>
              </div>

              <div className="flex items-center flex-shrink-0 ml-2">
                {pdf.visit_count > 0 && !isActive && (
                  <span className="text-[10px] font-bold bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full border border-emerald-100 mr-2 group-hover:opacity-0 transition-opacity">
                    {pdf.visit_count}
                  </span>
                )}
                {pdf.visit_count > 0 && isActive && (
                  <span className="text-[10px] font-bold bg-white/20 text-white px-2 py-0.5 rounded-full mr-2">
                    {pdf.visit_count}
                  </span>
                )}
                
                <button
                  onClick={(e) => handleDelete(e, pdf.id)}
                  className={`p-1.5 rounded-md transition-all opacity-0 group-hover:opacity-100 ${
                    isActive ? "hover:bg-red-500/30 text-red-200 hover:text-white" : "hover:bg-red-50 text-slate-400 hover:text-red-500"
                  }`}
                  title="Delete Document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}