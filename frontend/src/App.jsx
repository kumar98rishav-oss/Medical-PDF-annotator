import React, { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import FileUpload from "./components/FileUpload";
import PDFLibrary from "./components/PDFLibrary";
import PageSidebar from "./components/PageSidebar";
import PDFViewer from "./components/PDFViewer";
import VisitForm from "./components/VisitForm";
import VisitList from "./components/VisitList";
import AdminPanel from "./components/AdminPanel";
import ResizeHandle from "./components/ResizeHandle";
import Footer from "./components/Footer";
import OnboardingModal from "./components/OnboardingModal";
import OverlapDialog from "./components/OverlapDialog";

import * as api from "./api";
import { FileSearch, ChevronLeft, ChevronRight, PanelLeftClose, PanelRightClose } from "lucide-react";

export default function App() {


  const [view, setView] = useState("workspace"); // "workspace" | "admin"

  // ── PDF state ──
  const [pdfId, setPdfId] = useState(null);
  const [pdfInfo, setPdfInfo] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1.5);

  // ── Visits ──
  const [visits, setVisits] = useState([]);
  const [editingVisit, setEditingVisit] = useState(null);

  // ── Overlap Dialog ──
  const [overlapDialog, setOverlapDialog] = useState(null); // { visitId, warnings, newVisit }

  // ── Facilities (for autocomplete) ──
  const [facilities, setFacilities] = useState([]);

  // ── Loading / errors ──
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  // ── Panel widths & collapsed state ──
  const [leftW, setLeftW] = useState(320);
  const [sidebarW, setSidebarW] = useState(70);
  const [rightW, setRightW] = useState(400);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [pageSidebarCollapsed, setPageSidebarCollapsed] = useState(true); // default hidden for cleaner look

  const clamp = (val, min, max) => Math.max(min, Math.min(max, val));

  // ── Load facilities on mount ──
  useEffect(() => {
    api.getFacilities().then(setFacilities).catch(() => {});
  }, []);

  // ── Load visits when PDF changes ──
  useEffect(() => {
    if (!pdfId) {
      setVisits([]);
      return;
    }
    api
      .getVisits(pdfId)
      .then(setVisits)
      .catch((e) => setError(e.message));
  }, [pdfId]);

  // ── Open a PDF for annotation ──
  const openPDF = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    setOverlapDialog(null);
    try {
      const info = await api.getPDFInfo(id);
      setPdfId(id);
      setPdfInfo(info);
      setCurrentPage(1);
      setEditingVisit(null);
      // Auto-collapse left panel on mobile or small screens could go here
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Handle new upload ──
  // localPath is provided when running in PyWebView (file already on disk)
  const handleUpload = useCallback(
    async (file, localPath) => {
      setLoading(true);
      setUploadProgress(0);
      setError(null);
      try {
        let result;
        if (localPath) {
          // Fast path: backend copies file directly — no HTTP byte transfer
          result = await api.uploadPDFLocalPath(localPath, file.name || localPath.split(/[\\/]/).pop());
        } else {
          // Standard path: stream file via HTTP with progress indicator
          result = await api.uploadPDFWithProgress(file, setUploadProgress);
        }
        openPDF(result.id);
      } catch (e) {
        setError(e.message);
        setLoading(false);
      }
    },
    [openPDF]
  );

  // ── Go to admin panel ──
  const goToAdmin = useCallback(() => {
    setView("admin");
  }, []);

  const goBackToWorkspace = useCallback(() => {
    setView("workspace");
  }, []);

  // ── Visit CRUD ──
  const addVisit = useCallback(
    async (visitData) => {
      try {
        const response = await api.createVisit(pdfId, visitData);
        const created = response.visit || response;
        const warnings = response.warnings || null;
        
        setVisits((prev) => [...prev, created]);
        if (warnings?.length) {
          setOverlapDialog({ visitId: created.id, warnings, newVisit: created });
        }
        
        const info = await api.getPDFInfo(pdfId);
        setPdfInfo(info);
        api.getFacilities().then(setFacilities).catch(() => {});
        return created;
      } catch (e) {
        throw e;
      }
    },
    [pdfId]
  );

  const editVisit = useCallback(
    async (visitId, visitData) => {
      try {
        const response = await api.updateVisit(pdfId, visitId, visitData);
        const updated = response.visit || response;
        const warnings = response.warnings || null;
        
        setVisits((prev) =>
          prev.map((v) => (v.id === visitId ? updated : v))
        );
        setEditingVisit(null);
        if (warnings?.length) {
          setOverlapDialog({ visitId: updated.id, warnings, newVisit: updated });
        }
        
        const info = await api.getPDFInfo(pdfId);
        setPdfInfo(info);
      } catch (e) {
        throw e;
      }
    },
    [pdfId]
  );

  const removeVisit = useCallback(
    async (visitId) => {
      try {
        await api.deleteVisit(pdfId, visitId);
        setVisits((prev) => prev.filter((v) => v.id !== visitId));
        const info = await api.getPDFInfo(pdfId);
        setPdfInfo(info);
      } catch (e) {
        setError(e.message);
      }
    },
    [pdfId]
  );

  // ── Overlap dialog handlers ──
  const handleKeepOverlap = useCallback(async () => {
    if (!overlapDialog) return;
    try {
      const updated = await api.updateVisit(pdfId, overlapDialog.visitId, { allow_overlap: true });
      const v = updated.visit || updated;
      setVisits((prev) => prev.map((x) => (x.id === v.id ? v : x)));
    } catch (e) {
      setError(e.message);
    } finally {
      setOverlapDialog(null);
    }
  }, [pdfId, overlapDialog]);

  const handleTrimPages = useCallback(async (newStart, newEnd) => {
    if (!overlapDialog) return;
    try {
      const updated = await api.updateVisit(pdfId, overlapDialog.visitId, {
        start_page: newStart,
        end_page: newEnd,
      });
      const v = updated.visit || updated;
      setVisits((prev) => prev.map((x) => (x.id === v.id ? v : x)));
      const info = await api.getPDFInfo(pdfId);
      setPdfInfo(info);
    } catch (e) {
      setError(e.message);
    } finally {
      setOverlapDialog(null);
    }
  }, [pdfId, overlapDialog]);

  const handleRemoveVisitFromDialog = useCallback(async () => {
    if (!overlapDialog) return;
    try {
      await api.deleteVisit(pdfId, overlapDialog.visitId);
      setVisits((prev) => prev.filter((v) => v.id !== overlapDialog.visitId));
      const info = await api.getPDFInfo(pdfId);
      setPdfInfo(info);
    } catch (e) {
      setError(e.message);
    } finally {
      setOverlapDialog(null);
    }
  }, [pdfId, overlapDialog]);

  // ── Compute marked pages ──
  const markedPages = new Map();
  const visitColors = [
    "#14b8a6", "#3b82f6", "#f59e0b", "#ef4444",
    "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    "#f97316", "#0B3C5D", "#a855f7", "#e11d48",
  ];
  visits.forEach((v, idx) => {
    const color = visitColors[idx % visitColors.length];
    for (let p = v.start_page; p <= v.end_page; p++) {
      markedPages.set(p, color);
    }
  });



  // ═══════════════════════════════════════════════════
  //  ADMIN VIEW
  // ═══════════════════════════════════════════════════
  if (view === "admin") {
    return <AdminPanel onBack={goBackToWorkspace} />;
  }

  // ═══════════════════════════════════════════════════
  //  MEDICAL RECORD ANNOTATOR (existing workspace)
  // ═══════════════════════════════════════════════════
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50 font-sans text-slate-800">
      <OnboardingModal />

      <Header

        onAdmin={goToAdmin}
        filename={pdfInfo?.filename}
        pageInfo={
          pdfInfo
            ? `${pdfInfo.marked_pages} / ${pdfInfo.page_count} pages marked`
            : "Workspace"
        }
        processProps={{ pdfId, pdfInfo, visitCount: visits.length }}
      />

      {error && (
        <div className="px-6 py-2 bg-red-500 text-white text-sm flex items-center shadow-md animate-fade-in z-40">
          <span className="flex-1 font-medium">{error}</span>
          <button
            className="ml-3 font-semibold hover:text-red-200 transition-colors"
            onClick={() => setError(null)}
          >
            DISMISS
          </button>
        </div>
      )}

      <OverlapDialog
        newVisit={overlapDialog?.newVisit}
        warnings={overlapDialog?.warnings}
        allVisits={visits}
        onKeepOverlap={handleKeepOverlap}
        onTrimPages={handleTrimPages}
        onRemoveVisit={handleRemoveVisitFromDialog}
        onClose={() => setOverlapDialog(null)}
      />

      <div className="flex flex-1 overflow-hidden relative">
        {/* ── Left Panel: Library & Upload ── */}
        {!leftCollapsed && (
          <div 
            style={{ width: leftW, minWidth: 260 }} 
            className="flex-shrink-0 flex flex-col border-r border-slate-200 bg-white shadow-soft z-20"
          >
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              <FileUpload onUpload={handleUpload} loading={loading} uploadProgress={uploadProgress} />
              <div className="border-t border-slate-100 pt-4 mt-2">
                <PDFLibrary onSelect={openPDF} activeId={pdfId} />
              </div>
            </div>
            <Footer />
          </div>
        )}
        {!leftCollapsed && (
          <ResizeHandle onResize={(dx) => setLeftW(w => clamp(w + dx, 260, 450))} />
        )}

        <button
          onClick={() => setLeftCollapsed(c => !c)}
          className={`absolute left-0 top-1/2 -translate-y-1/2 z-30 w-6 h-12 flex items-center justify-center bg-white border border-slate-200 shadow-md rounded-r-lg hover:bg-slate-50 transition-all ${!leftCollapsed && leftW ? `ml-[${leftW}px]` : ""}`}
          style={{ marginLeft: !leftCollapsed ? leftW + (4) : 0 }}
          title={leftCollapsed ? "Show Library" : "Hide Library"}
        >
          {leftCollapsed ? <ChevronRight className="w-4 h-4 text-slate-500" /> : <ChevronLeft className="w-4 h-4 text-slate-500" />}
        </button>


        {/* ── Center Panel: PDF Viewer area ── */}
        <div className="flex-1 flex overflow-hidden bg-slate-100/50 min-w-[300px] relative">
          
          {pdfId ? (
            <>
              {/* Optional embedded PageSidebar */}
              {!pageSidebarCollapsed && (
                <div style={{ width: sidebarW, minWidth: 60 }} className="flex-shrink-0 border-r border-slate-200 bg-white/80 backdrop-blur-sm z-10 transition-all">
                  <PageSidebar
                    pageCount={pdfInfo?.page_count || 0}
                    currentPage={currentPage}
                    markedPages={markedPages}
                    onPageClick={setCurrentPage}
                  />
                </div>
              )}
              
              <button
                onClick={() => setPageSidebarCollapsed(c => !c)}
                className="absolute left-0 top-4 z-20 w-8 h-8 flex items-center justify-center bg-white border border-slate-200 shadow-soft rounded-r-md hover:bg-brand-light/10 hover:text-brand-dark transition-all"
                title="Toggle Page Index"
                style={{ marginLeft: !pageSidebarCollapsed ? sidebarW : 0 }}
              >
                {pageSidebarCollapsed ? <PanelLeftClose className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
              </button>

              <div className="flex-1 flex flex-col relative w-full h-full">
                 <PDFViewer
                  pdfId={pdfId}
                  currentPage={currentPage}
                  totalPages={pdfInfo?.page_count || 0}
                  zoom={zoom}
                  onPageChange={setCurrentPage}
                  onZoomChange={setZoom}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center bg-slate-50">
              <div className="w-24 h-24 mb-6 rounded-3xl bg-white shadow-soft flex items-center justify-center text-brand-light">
                <FileSearch className="w-12 h-12" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">No Document Selected</h2>
              <p className="text-slate-500 max-w-sm text-center">
                Select a document from the library on the left or upload a new PDF to begin annotating.
              </p>
            </div>
          )}
        </div>

        {/* ── Right Panel Toggle ── */}
        {pdfId && (
          <button
            onClick={() => setRightCollapsed(c => !c)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-30 w-6 h-12 flex items-center justify-center bg-white border border-slate-200 shadow-md rounded-l-lg hover:bg-slate-50 transition-all"
            style={{ marginRight: !rightCollapsed ? rightW + 4 : 0 }}
            title={rightCollapsed ? "Show Annotations" : "Hide Annotations"}
          >
            {rightCollapsed ? <ChevronLeft className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
          </button>
        )}

        {/* ── Right Panel: Annotation Tools ── */}
        {pdfId && !rightCollapsed && (
          <>
            <ResizeHandle onResize={(dx) => setRightW(w => clamp(w - dx, 320, 650))} />
            <div 
              style={{ width: rightW, minWidth: 320 }} 
              className="bg-white border-l border-slate-200 flex flex-col overflow-hidden flex-shrink-0 shadow-soft z-20"
            >
              <div className="flex-1 overflow-y-auto p-4 space-y-5 custom-scrollbar">
                <VisitForm
                  pdfId={pdfId}
                  currentPage={currentPage}
                  totalPages={pdfInfo?.page_count || 0}
                  facilities={facilities}
                  onSubmit={addVisit}
                  editingVisit={editingVisit}
                  onUpdate={editVisit}
                  onCancelEdit={() => setEditingVisit(null)}
                />

                <VisitList
                  visits={visits}
                  colors={visitColors}
                  onGoTo={(page) => setCurrentPage(page)}
                  onEdit={setEditingVisit}
                  onDelete={removeVisit}
                />
              </div>
            </div>
          </>
        )}
        
      </div>
    </div>
  );
}