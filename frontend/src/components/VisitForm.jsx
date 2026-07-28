import React, { useState, useEffect } from "react";
import { Edit2, Plus, MapPin, Sparkles, Loader2, X, Camera, Car, FileText, Receipt, FolderOpen } from "lucide-react";
import * as api from "../api";

const DOCUMENT_TYPES = [
  { value: "progress_note", label: "Progress Note" },
  { value: "consultation_note", label: "Consultation Note" },
  { value: "discharge_summary", label: "Discharge Summary" },
  { value: "operative_note", label: "Operative Note" },
  { value: "procedure_note", label: "Procedure Note" },
  { value: "emergency_note", label: "Emergency Note" },
  { value: "radiology_report", label: "Radiology Report" },
  { value: "imaging_report", label: "Imaging Report" },
  { value: "lab_report", label: "Lab Report" },
  { value: "pathology_report", label: "Pathology Report" },
  { value: "nursing_note", label: "Nursing Note" },
  { value: "therapy_note", label: "Therapy Note" },
  { value: "prescription", label: "Prescription" },
  { value: "intake_form", label: "Intake Form" },
  { value: "insurance_authorization", label: "Insurance Authorization" },
  { value: "referral", label: "Referral" },
  { value: "other", label: "Other" },
];

const SECTION_TYPES = [
  { value: "medical_record", label: "Medical Record", icon: FileText, color: "teal", bgClass: "bg-teal-50 text-teal-700 border-teal-300 ring-teal-400" },
  { value: "medical_bill",   label: "Medical Bill",   icon: Receipt,  color: "blue", bgClass: "bg-blue-50 text-blue-700 border-blue-300 ring-blue-400" },
  { value: "injury_photo",   label: "Injury Photos",  icon: Camera,   color: "rose", bgClass: "bg-rose-50 text-rose-700 border-rose-300 ring-rose-400" },
  { value: "vehicle_photo",  label: "Vehicle Photos", icon: Car,      color: "amber", bgClass: "bg-amber-50 text-amber-700 border-amber-300 ring-amber-400" },
  { value: "other",          label: "Other",          icon: FolderOpen, color: "slate", bgClass: "bg-slate-100 text-slate-700 border-slate-300 ring-slate-400" },
];

// Sections that need facility/DOS/provider metadata
const MEDICAL_SECTIONS = new Set(["medical_record", "medical_bill"]);
// Sections that are simple page ranges (no metadata)
const SIMPLE_SECTIONS = new Set(["injury_photo", "vehicle_photo", "other"]);

const INITIAL_FORM = {
  start_page: "",
  end_page: "",
  date_of_service: "",
  facility_name: "",
  provider_name: "",
  document_type: "Progress Note",
  section_type: "medical_record",
  notes: "",
};

function SuggestionChips({ label, items, onPick, color = "primary" }) {
  if (!items || items.length === 0) return null;

  const colorMap = {
    primary: "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 hover:border-blue-300",
    teal: "bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-100 hover:border-teal-300",
    amber: "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 hover:border-amber-300",
    violet: "bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100 hover:border-violet-300",
  };

  return (
    <div className="mt-1.5">
      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{label}</span>
      <div className="flex flex-wrap gap-1.5 mt-1">
        {items.map((item, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onPick(item)}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded-full border cursor-pointer transition-all duration-150 active:scale-95 ${colorMap[color]}`}
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function KnownFacilityCards({ facilities, onPick }) {
  if (!facilities || facilities.length === 0) return null;

  return (
    <div className="mt-2">
      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Known Facilities</span>
      <div className="mt-1 space-y-1.5 max-h-36 overflow-y-auto custom-scrollbar">
        {facilities.map((f, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onPick(f)}
            className="w-full text-left px-3 py-2 bg-slate-50 hover:bg-primary-50 border border-slate-200 hover:border-primary-300 rounded-lg transition-all duration-150 group"
          >
            <div className="text-[12px] font-semibold text-slate-700 group-hover:text-primary-700">
              {f.facility_name}
            </div>
            {f.common_providers && f.common_providers.length > 0 && (
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                Providers: {f.common_providers.slice(0, 3).join(", ")}
              </div>
            )}
            {f.times_seen && (
              <div className="text-[9px] text-slate-400 mt-0.5">{f.times_seen}× seen</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function VisitForm({
  pdfId,
  currentPage,
  totalPages,
  facilities,
  onSubmit,
  editingVisit,
  onUpdate,
  onCancelEdit,
}) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Suggestion state
  const [suggestions, setSuggestions] = useState(null);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [suggestError, setSuggestError] = useState(null);

  // Populate form when editing
  useEffect(() => {
    if (editingVisit) {
      setForm({
        start_page: editingVisit.start_page,
        end_page: editingVisit.end_page,
        date_of_service: editingVisit.date_of_service || "",
        facility_name: editingVisit.facility_name || "",
        provider_name: editingVisit.provider_name || "",
        document_type: editingVisit.document_type || "other",
        section_type: editingVisit.section_type || "medical_record",
        notes: editingVisit.notes || "",
      });
      setSuggestions(null);
    }
  }, [editingVisit]);

  // Auto-update End Page when navigating pages
  useEffect(() => {
    if (!editingVisit && currentPage) {
      setForm((prev) => ({ ...prev, end_page: currentPage }));
    }
  }, [currentPage, editingVisit]);

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const currentSectionType = form.section_type;
  const isMedical = MEDICAL_SECTIONS.has(currentSectionType);
  const isSimple = SIMPLE_SECTIONS.has(currentSectionType);
  const showDocType = currentSectionType === "medical_record";
  const showFacility = isMedical;
  const showDOS = isMedical;
  const showProvider = isMedical;
  const showSmartSuggest = isMedical;

  // ── Smart Suggest ──
  const handleSuggest = async () => {
    const startPage = parseInt(form.start_page);
    const endPage = parseInt(form.end_page);

    if (!startPage || !endPage || startPage < 1 || endPage < 1) {
      setSuggestError("Set valid start and end pages first");
      return;
    }
    if (startPage > endPage) {
      setSuggestError("Start page must be ≤ end page");
      return;
    }
    if (!pdfId) {
      setSuggestError("No PDF loaded");
      return;
    }

    setSuggestLoading(true);
    setSuggestError(null);
    setSuggestions(null);

    try {
      const result = await api.quickAnnotate(pdfId, startPage, endPage);
      setSuggestions(result);
    } catch (e) {
      setSuggestError(e.message);
    } finally {
      setSuggestLoading(false);
    }
  };

  const handleAISuggest = async () => {
    let apiKey = localStorage.getItem("openai_api_key");
    if (!apiKey) {
      apiKey = window.prompt("To use the AI Deep Scan, please enter your OpenAI API Key (it will be saved securely on your device):");
      if (!apiKey) return;
      localStorage.setItem("openai_api_key", apiKey.trim());
    }

    const startPage = parseInt(form.start_page);
    const endPage = parseInt(form.end_page);

    if (!startPage || !endPage || startPage < 1 || endPage < 1) {
      setSuggestError("Set valid start and end pages first");
      return;
    }
    if (startPage > endPage) {
      setSuggestError("Start page must be ≤ end page");
      return;
    }
    if (!pdfId) {
      setSuggestError("No PDF loaded");
      return;
    }

    setAiLoading(true);
    setSuggestError(null);
    setSuggestions(null);

    try {
      const result = await api.aiAnnotate(pdfId, startPage, endPage, apiKey.trim());
      setSuggestions(result);
    } catch (e) {
      if (e.message.toLowerCase().includes("api key") || e.message.includes("401")) {
        localStorage.removeItem("openai_api_key");
        setSuggestError("Invalid API Key. Please click Deep Scan to try again.");
      } else {
        setSuggestError(e.message);
      }
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const startPage = parseInt(form.start_page);
    const endPage = parseInt(form.end_page);

    if (!startPage || !endPage) {
      setError("Start and end page are required");
      return;
    }
    if (startPage < 1 || endPage > totalPages) {
      setError(`Pages must be between 1 and ${totalPages}`);
      return;
    }
    if (startPage > endPage) {
      setError("Start page must be ≤ end page");
      return;
    }

    const payload = {
      start_page: startPage,
      end_page: endPage,
      section_type: form.section_type,
      date_of_service: isMedical ? form.date_of_service.trim() : "",
      facility_name: isMedical ? form.facility_name.trim() : "",
      provider_name: isMedical ? form.provider_name.trim() : "",
      document_type: showDocType ? form.document_type : (currentSectionType === "medical_bill" ? "medical_bill" : form.section_type),
      notes: form.notes.trim(),
    };

    setSubmitting(true);
    try {
      if (editingVisit) {
        await onUpdate(editingVisit.id, payload);
      } else {
        await onSubmit(payload);
      }
      setForm(INITIAL_FORM);
      setSuggestions(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isEditing = !!editingVisit;

  // Facility names for autocomplete
  const facilityNames = facilities.map((f) => f.facility_name);

  const inputClass = "w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-slate-50/50 focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 focus:bg-white transition-all outline-none placeholder:text-slate-400";
  const labelClass = "block text-[10px] font-semibold text-slate-500 mb-1 uppercase tracking-wider";

  const hasSuggestions = suggestions && (
    suggestions.facilities?.length > 0 ||
    suggestions.providers?.length > 0 ||
    suggestions.dates_of_service?.length > 0 ||
    suggestions.document_types?.length > 0 ||
    suggestions.known_facilities?.length > 0
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3 bg-white p-3.5 rounded-xl border border-slate-100 shadow-sm">
      <h3 className="font-bold text-brand-dark text-[13px] uppercase tracking-wider flex items-center gap-2 mb-2">
        {isEditing ? <><Edit2 className="w-4 h-4 text-brand-light" /> Edit Visit</> : <><Plus className="w-4 h-4 text-primary-500" /> Add Visit</>}
      </h3>

      {error && (
        <div className="text-xs text-red-700 font-medium bg-red-50 border border-red-200 px-3 py-2.5 rounded-xl">
          {error}
        </div>
      )}

      {/* ── Section Type Selector ── */}
      <div>
        <label className={labelClass}>Section Type</label>
        <div className="grid grid-cols-3 gap-1.5">
          {SECTION_TYPES.map((sec) => {
            const Icon = sec.icon;
            const active = form.section_type === sec.value;
            return (
              <button
                key={sec.value}
                type="button"
                onClick={() => {
                  updateField("section_type", sec.value);
                  setSuggestions(null);
                }}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-[10px] font-bold border transition-all duration-150 ${
                  active
                    ? `${sec.bgClass} ring-2 ring-offset-1`
                    : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:border-slate-300"
                }`}
              >
                <Icon className="w-3 h-3" />
                {sec.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Page range */}
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className={labelClass}>Start Page</label>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              max={totalPages}
              value={form.start_page}
              onChange={(e) => updateField("start_page", e.target.value)}
              className={inputClass}
              placeholder="1"
            />
            <button
              type="button"
              onClick={() => updateField("start_page", currentPage)}
              className="px-2.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200 transition-colors flex-shrink-0"
              title="Set to current page"
            >
              <MapPin className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1">
          <label className={labelClass}>End Page</label>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              max={totalPages}
              value={form.end_page}
              onChange={(e) => updateField("end_page", e.target.value)}
              className={inputClass}
              placeholder="5"
            />
            <button
              type="button"
              onClick={() => updateField("end_page", currentPage)}
              className="px-2.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg border border-slate-200 transition-colors flex-shrink-0"
              title="Set to current page"
            >
              <MapPin className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Smart Suggest Buttons (only for medical sections) ── */}
      {showSmartSuggest && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSuggest}
            disabled={suggestLoading || aiLoading}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all duration-200 border bg-gradient-to-r from-violet-500 to-indigo-500 text-white border-violet-400 hover:from-violet-600 hover:to-indigo-600 active:scale-[0.98] shadow-sm disabled:opacity-60"
          >
            {suggestLoading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Scanning...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5" /> Smart Suggest</>
            )}
          </button>
          <button
            type="button"
            onClick={handleAISuggest}
            disabled={suggestLoading || aiLoading}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all duration-200 border bg-slate-800 text-white hover:bg-slate-900 active:scale-[0.98] shadow-sm disabled:opacity-60"
            title="Use Cloud AI to extract complex layouts flawlessly"
          >
            {aiLoading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> AI Deep Scan...</>
            ) : (
              <><Sparkles className="w-3.5 h-3.5 text-amber-300" /> Deep AI Scan</>
            )}
          </button>
        </div>
      )}

      {suggestError && (
        <div className="text-xs text-amber-700 font-medium bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg">
          {suggestError}
        </div>
      )}

      {/* ── Suggestions Panel ── */}
      {hasSuggestions && showSmartSuggest && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-2 animate-fade-in">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-violet-500" /> Suggestions Found
            </span>
            <button
              type="button"
              onClick={() => setSuggestions(null)}
              className="p-1 hover:bg-slate-200 rounded-md transition-colors"
            >
              <X className="w-3 h-3 text-slate-400" />
            </button>
          </div>

          <SuggestionChips
            label="Dates of Service"
            items={suggestions.dates_of_service}
            onPick={(val) => updateField("date_of_service", val)}
            color="amber"
          />
          <SuggestionChips
            label="Facilities (from text)"
            items={suggestions.facilities}
            onPick={(val) => updateField("facility_name", val)}
            color="primary"
          />
          <SuggestionChips
            label="Providers (from text)"
            items={suggestions.providers}
            onPick={(val) => updateField("provider_name", val)}
            color="teal"
          />
          {showDocType && (
            <SuggestionChips
              label="Document Types"
              items={suggestions.document_types}
              onPick={(val) => updateField("document_type", val)}
              color="violet"
            />
          )}
          <KnownFacilityCards
            facilities={suggestions.known_facilities}
            onPick={(f) => {
              updateField("facility_name", f.facility_name);
              // Auto-fill provider from known facility if empty
              if (!form.provider_name && f.common_providers?.length > 0) {
                updateField("provider_name", f.common_providers[0]);
              }
              // Auto-fill doc type from known facility if still default
              if (showDocType && form.document_type === "Progress Note" && f.common_doc_types?.length > 0) {
                updateField("document_type", f.common_doc_types[0]);
              }
            }}
          />
        </div>
      )}

      {/* Date & Document Type Row (medical sections only) */}
      {isMedical && (
        <div className="flex gap-3">
          {showDOS && (
            <div className="flex-1">
              <label className={labelClass}>Date of Service</label>
              <input
                type="text"
                value={form.date_of_service}
                onChange={(e) => updateField("date_of_service", e.target.value)}
                className={inputClass}
                placeholder="03/15/2024"
              />
            </div>
          )}

          {showDocType && (
            <div className="flex-1">
              <label className={labelClass}>Doc Type</label>
              <input
                type="text"
                list="doctype-list"
                value={form.document_type}
                onChange={(e) => updateField("document_type", e.target.value)}
                className={inputClass}
                placeholder="Progress Note"
              />
              <datalist id="doctype-list">
                {DOCUMENT_TYPES.map((dt) => (
                  <option key={dt.value} value={dt.label} />
                ))}
              </datalist>
            </div>
          )}
        </div>
      )}

      {/* Facility & Provider Row (medical sections only) */}
      {showFacility && (
        <div className="flex gap-3">
          <div className="flex-1">
            <label className={labelClass}>Facility Name {isMedical && "*"}</label>
            <input
              type="text"
              list="facility-list"
              value={form.facility_name}
              onChange={(e) => updateField("facility_name", e.target.value)}
              className={inputClass}
              placeholder="Hospital Name"
            />
            <datalist id="facility-list">
              {facilityNames.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </div>

          {showProvider && (
            <div className="flex-1">
              <label className={labelClass}>Provider Name</label>
              <input
                type="text"
                value={form.provider_name}
                onChange={(e) => updateField("provider_name", e.target.value)}
                className={inputClass}
                placeholder="Dr. Smith"
              />
            </div>
          )}
        </div>
      )}

      {/* Notes */}
      <div>
        <label className={labelClass}>
          Notes <span className="text-slate-400 font-normal lowercase">(optional)</span>
        </label>
        <input
          type="text"
          value={form.notes}
          onChange={(e) => updateField("notes", e.target.value)}
          className={inputClass}
          placeholder="Any additional context..."
        />
      </div>

      {/* Buttons */}
      <div className="flex gap-2 pt-0.5">
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 text-white py-2 rounded-lg text-sm font-semibold hover:from-primary-700 hover:to-primary-800 active:scale-[0.98] transition-all shadow-md disabled:opacity-50"
        >
          {submitting ? "Saving..." : isEditing ? "Update Visit" : "Add Visit"}
        </button>
        {isEditing && (
          <button
            type="button"
            onClick={() => {
              onCancelEdit();
              setForm(INITIAL_FORM);
              setSuggestions(null);
            }}
            className="px-4 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg text-sm hover:bg-slate-200 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}