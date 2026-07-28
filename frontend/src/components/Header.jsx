import React from "react";
import ProcessDropdown from "./ProcessDropdown";
import { Activity, Settings } from "lucide-react";

export default function Header({ onAdmin, filename, pageInfo, processProps }) {
  return (
    <header className="bg-brand-dark border-b border-white/10 px-4 py-2 flex items-center justify-between shadow-md relative z-30">
      <div className="flex items-center gap-4">

        <div className="flex items-center gap-3">
          <div className="bg-brand-blue/30 p-2 rounded-xl border border-brand-light/30 shadow-inner">
            <Activity className="w-5 h-5 text-brand-light" />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <h1 className="text-[17px] font-bold text-white tracking-tight">
                MedAnnotate AI
              </h1>
              <span className="text-[10px] text-brand-light font-semibold tracking-widest uppercase opacity-90 hidden sm:block">
                Powered by Rishav.K
              </span>
            </div>
            {filename && (
              <p className="text-xs font-medium text-slate-300 mt-0.5 truncate max-w-md hidden sm:block">
                {filename}
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {/* Process / Download dropdown */}
        {processProps && (
          <ProcessDropdown
            pdfId={processProps.pdfId}
            pdfInfo={processProps.pdfInfo}
            visitCount={processProps.visitCount}
          />
        )}
        {pageInfo && (
          <span className="text-[11px] font-bold text-brand-light bg-brand-blue/20 border border-brand-light/20 px-3 py-1 rounded-full shadow-inner tracking-wide">
            {pageInfo}
          </span>
        )}
        {onAdmin && (
          <button
            onClick={onAdmin}
            className="p-2 text-slate-300 hover:text-white hover:bg-white/10 rounded-lg transition-all"
            title="Admin Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        )}
      </div>
    </header>
  );
}