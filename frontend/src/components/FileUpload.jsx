import React, { useRef, useState } from "react";

export default function FileUpload({ onUpload, loading, uploadProgress }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please select a PDF file.");
      return;
    }
    // PyWebView exposes file.path on drag-and-drop — use fast local copy when available
    const localPath = file.path && typeof file.path === "string" && file.path.length > 3
      ? file.path
      : null;
    onUpload(file, localPath);
  };

  const handleClick = async () => {
    // Use native file dialog via PyWebView when running as a desktop app
    if (window.pywebview && window.pywebview.api) {
      try {
        const result = await window.pywebview.api.open_file_dialog();
        if (result && result.path) {
          onUpload({ name: result.filename }, result.path);
        }
        return;
      } catch {
        // Fall through to browser file input if the API call fails
      }
    }
    inputRef.current?.click();
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const showProgress = loading && typeof uploadProgress === "number" && uploadProgress > 0;

  return (
    <div
      className={`relative group border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center transition-all duration-300 cursor-pointer mb-6 ${
        dragOver
          ? "border-primary-500 bg-primary-50 scale-[1.02] shadow-soft"
          : "border-slate-300 bg-white hover:border-primary-400 hover:bg-slate-50 hover:shadow-soft"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {loading ? (
        <div className="flex flex-col items-center gap-3 w-full">
          <div className="w-8 h-8 border-3 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-600 font-medium text-sm animate-pulse">
            {showProgress ? `Uploading… ${uploadProgress}%` : "Processing…"}
          </p>
          {showProgress && (
            <div className="w-full bg-slate-200 rounded-full h-1.5">
              <div
                className="bg-primary-500 h-1.5 rounded-full transition-all duration-200"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="bg-primary-50 p-3 rounded-full text-primary-500 group-hover:bg-primary-100 transition-colors shadow-sm">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Upload PDF</p>
            <p className="text-xs text-slate-500 mt-1 font-medium">Drag & drop or click</p>
          </div>
        </div>
      )}
    </div>
  );
}
