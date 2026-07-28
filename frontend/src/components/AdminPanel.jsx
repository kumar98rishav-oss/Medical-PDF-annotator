import React, { useState, useEffect, useCallback } from "react";
import * as api from "../api";

export default function AdminPanel({ onBack }) {
  const [stats, setStats] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetInput, setResetInput] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [storageStats, logs] = await Promise.all([
        api.getStorageStats(),
        api.getAuditLog ? api.getAuditLog() : Promise.resolve([]),
      ]);
      setStats(storageStats);
      setAuditLog(Array.isArray(logs) ? logs : []);
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCleanup = async () => {
    setActionLoading("cleanup");
    setMessage(null);
    try {
      const res = await api.cleanupOrphans();
      setMessage({
        type: "success",
        text: `Cleanup complete — ${res.deleted_files} orphaned file(s) removed.`,
      });
      loadData();
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReset = async () => {
    if (resetInput !== "RESET_ALL_DATA") return;
    setActionLoading("reset");
    setMessage(null);
    try {
      await api.factoryReset("RESET_ALL_DATA");
      setMessage({
        type: "success",
        text: "Factory reset complete. All data has been cleared.",
      });
      setShowResetConfirm(false);
      setResetInput("");
      loadData();
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setActionLoading(null);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes && bytes !== 0) return "—";
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatDate = (dt) => {
    if (!dt) return "—";
    return new Date(dt).toLocaleString();
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 border-b border-primary-900 px-4 py-1.5 flex items-center justify-between shadow-sm relative z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-all duration-200"
            title="Back to library"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex items-center gap-2.5">
            <div className="bg-amber-500/10 p-1.5 rounded-lg border border-amber-500/20">
              <span className="text-base leading-none block">⚙️</span>
            </div>
            <h1 className="text-base font-bold text-white tracking-tight">
              Admin Panel
            </h1>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Messages */}
        {message && (
          <div
            className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between ${
              message.type === "error"
                ? "bg-red-50 border border-red-200 text-red-700"
                : "bg-emerald-50 border border-emerald-200 text-emerald-700"
            }`}
          >
            <span>{message.text}</span>
            <button
              className="ml-3 underline opacity-70 hover:opacity-100"
              onClick={() => setMessage(null)}
            >
              dismiss
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* ── Storage Stats ── */}
            <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
                <span className="text-lg">📊</span>
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  Storage Overview
                </h2>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-slate-100">
                {[
                  {
                    label: "Uploads",
                    value: formatBytes(stats?.uploads_size),
                    count: stats?.uploads_count,
                    icon: "📄",
                    color: "text-blue-600",
                  },
                  {
                    label: "Processed",
                    value: formatBytes(stats?.processed_size),
                    count: stats?.processed_count,
                    icon: "✅",
                    color: "text-emerald-600",
                  },
                  {
                    label: "Logs",
                    value: formatBytes(stats?.logs_size),
                    count: stats?.logs_count,
                    icon: "📋",
                    color: "text-amber-600",
                  },
                  {
                    label: "Database",
                    value: formatBytes(stats?.database_size),
                    count: null,
                    icon: "🗃️",
                    color: "text-purple-600",
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="bg-white p-5 flex flex-col items-center text-center"
                  >
                    <span className="text-2xl mb-2">{item.icon}</span>
                    <p className={`text-lg font-bold ${item.color}`}>
                      {item.value}
                    </p>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">
                      {item.label}
                      {item.count != null && (
                        <span className="text-slate-400"> · {item.count} files</span>
                      )}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* ── Maintenance Actions ── */}
            <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
                <span className="text-lg">🔧</span>
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  Maintenance
                </h2>
              </div>
              <div className="p-6 space-y-4">
                {/* Cleanup Orphans */}
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                  <div>
                    <h3 className="text-sm font-bold text-slate-700">
                      Clean Orphaned Files
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Remove files on disk that are no longer tracked in the
                      database.
                    </p>
                  </div>
                  <button
                    onClick={handleCleanup}
                    disabled={actionLoading === "cleanup"}
                    className="px-5 py-2 bg-amber-500 text-white rounded-lg text-sm font-bold hover:bg-amber-600 active:scale-[0.97] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                  >
                    {actionLoading === "cleanup" ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Cleaning...
                      </span>
                    ) : (
                      "🧹 Run Cleanup"
                    )}
                  </button>
                </div>

                {/* Factory Reset */}
                <div className="flex items-center justify-between p-4 bg-red-50/50 rounded-xl border border-red-100">
                  <div>
                    <h3 className="text-sm font-bold text-red-700">
                      Factory Reset
                    </h3>
                    <p className="text-xs text-red-500/80 mt-0.5">
                      Delete ALL data — uploads, processed files, database,
                      and logs. This cannot be undone.
                    </p>
                  </div>
                  {!showResetConfirm ? (
                    <button
                      onClick={() => setShowResetConfirm(true)}
                      className="px-5 py-2 bg-red-500 text-white rounded-lg text-sm font-bold hover:bg-red-600 active:scale-[0.97] transition-all shadow-sm"
                    >
                      ⚠️ Reset
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={resetInput}
                        onChange={(e) => setResetInput(e.target.value)}
                        placeholder='Type "RESET_ALL_DATA"'
                        className="px-3 py-1.5 border border-red-300 rounded-lg text-xs font-mono w-44 focus:ring-2 focus:ring-red-400"
                      />
                      <button
                        onClick={handleReset}
                        disabled={
                          resetInput !== "RESET_ALL_DATA" ||
                          actionLoading === "reset"
                        }
                        className="px-4 py-1.5 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => {
                          setShowResetConfirm(false);
                          setResetInput("");
                        }}
                        className="px-3 py-1.5 bg-slate-200 text-slate-600 rounded-lg text-xs font-bold hover:bg-slate-300"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/* ── Audit Log ── */}
            {auditLog.length > 0 && (
              <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2.5">
                  <span className="text-lg">📜</span>
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                    Recent Activity
                  </h2>
                  <span className="ml-auto text-[10px] font-bold text-slate-400 bg-slate-100 px-2.5 py-1 rounded-full">
                    {auditLog.length} entries
                  </span>
                </div>
                <div className="max-h-72 overflow-y-auto divide-y divide-slate-50">
                  {auditLog.map((log) => (
                    <div
                      key={log.id}
                      className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50/50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-slate-700 truncate">
                          {log.action}
                        </p>
                        {log.entity_type && (
                          <p className="text-[10px] text-slate-400 mt-0.5">
                            {log.entity_type}
                            {log.entity_id && ` · ${log.entity_id.slice(0, 8)}…`}
                          </p>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium whitespace-nowrap">
                        {formatDate(log.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
