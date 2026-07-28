/**
 * API client for Medical PDF Annotator backend (v2)
 */

const BASE = "/api";

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.error) {
        detail = body.error;
      } else if (body.detail) {
        if (Array.isArray(body.detail)) {
          detail = body.detail.map(e => `${e.loc?.join('.')} ${e.msg}`).join(', ');
        } else if (typeof body.detail === 'object') {
          detail = JSON.stringify(body.detail);
        } else {
          detail = body.detail;
        }
      } else {
        detail = JSON.stringify(body);
      }
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ─── PDF Upload & Info ──────────────────────────────

export async function uploadPDF(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.error || body.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return res.json();
}

/** Upload with progress callback (0–100). Falls back to fetch if XHR unavailable. */
export function uploadPDFWithProgress(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)); }
        catch { reject(new Error("Invalid server response")); }
      } else {
        let detail = `Upload failed (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          detail = body.error || body.detail || detail;
        } catch {}
        reject(new Error(detail));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.open("POST", `${BASE}/upload`);
    xhr.send(form);
  });
}

/** Fast local-path upload — backend copies the file directly on disk. */
export async function uploadPDFLocalPath(filePath, filename) {
  const res = await fetch(`${BASE}/upload/local-path`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: filePath, filename }),
  });

  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.error || body.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return res.json();
}

export function listPDFs() {
  return request("/pdfs");
}

export function getPDFInfo(pdfId) {
  return request(`/pdf/${pdfId}/info`);
}

export function deletePDF(pdfId) {
  return request(`/pdf/${pdfId}`, { method: "DELETE" });
}

export function pageImageURL(pdfId, pageNum, zoom = 1.5) {
  return `${BASE}/pdf/${pdfId}/page/${pageNum}/image?zoom=${zoom}`;
}

// ─── Visit Annotations ─────────────────────────────
// NOTE: createVisit and updateVisit now return { visit, warnings }

export function getVisits(pdfId) {
  return request(`/pdf/${pdfId}/visits`);
}

export function createVisit(pdfId, visitData) {
  return request(`/pdf/${pdfId}/visits`, {
    method: "POST",
    body: JSON.stringify(visitData),
  });
}

export function updateVisit(pdfId, visitId, visitData) {
  return request(`/pdf/${pdfId}/visits/${visitId}`, {
    method: "PUT",
    body: JSON.stringify(visitData),
  });
}

export function deleteVisit(pdfId, visitId) {
  return request(`/pdf/${pdfId}/visits/${visitId}`, {
    method: "DELETE",
  });
}

// ─── Facilities ─────────────────────────────────────

export function getFacilities() {
  return request("/facilities");
}

// ─── Smart Suggestions (quick-annotate) ─────────────

export function quickAnnotate(pdfId, startPage, endPage) {
  return request(`/pdf/${pdfId}/quick-annotate`, {
    method: "POST",
    body: JSON.stringify({ start_page: startPage, end_page: endPage }),
  });
}

export function aiAnnotate(pdfId, startPage, endPage, apiKey) {
  return request(`/pdf/${pdfId}/ai-annotate`, {
    method: "POST",
    body: JSON.stringify({ start_page: startPage, end_page: endPage, api_key: apiKey }),
  });
}

export function quickOCR(pdfId, startPage, endPage) {
  return request(`/pdf/${pdfId}/quick-ocr`, {
    method: "POST",
    body: JSON.stringify({ start_page: startPage, end_page: endPage }),
  });
}

export function getPDFStatus(pdfId) {
  return request(`/pdf/${pdfId}/status`);
}

// ─── Processing (v2: dual mode) ─────────────────────

export function processPDF(pdfId, mode = "combined") {
  return request(`/pdf/${pdfId}/process?mode=${mode}`, { method: "POST" });
}

export function getProcessStatus(jobId) {
  return request(`/process/status/${jobId}`);
}

export function downloadURL(processId) {
  return `${BASE}/download/${processId}`;
}

export function downloadURLLegacy(processId) {
  return `${BASE}/processed/${processId}/download`;
}

export function getProcessedVersions(pdfId) {
  return request(`/pdf/${pdfId}/processed`);
}

// ─── Admin / Lifecycle ──────────────────────────────

export function getStorageStats() {
  return request("/admin/storage-stats");
}

export function cleanupOrphans() {
  return request("/admin/cleanup-orphans", { method: "POST" });
}

export function factoryReset(confirmToken) {
  return request("/admin/factory-reset", {
    method: "DELETE",
    body: JSON.stringify({ confirm: confirmToken }),
  });
}

export function saveSession(key, value) {
  return request("/admin/session", {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

export function restoreSession() {
  return request("/admin/session");
}

export function getAuditLog(limit = 50) {
  return request(`/admin/audit-log?limit=${limit}`);
}