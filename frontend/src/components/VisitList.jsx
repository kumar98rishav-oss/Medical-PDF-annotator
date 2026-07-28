import React, { useState } from "react";
import { Eye, Edit2, Trash2, List as ListIcon, ChevronRight, Camera, Car, FileText, Receipt, FolderOpen } from "lucide-react";

const SECTION_META = {
  injury_photo:   { label: "Injury Photo",  icon: Camera,     color: "#e11d48", bgColor: "#fff1f2" },
  vehicle_photo:  { label: "Vehicle Photo", icon: Car,        color: "#d97706", bgColor: "#fffbeb" },
  medical_record: { label: "Medical Record", icon: FileText,  color: "#0d9488", bgColor: "#f0fdfa" },
  medical_bill:   { label: "Medical Bill",   icon: Receipt,   color: "#2563eb", bgColor: "#eff6ff" },
  other:          { label: "Other",          icon: FolderOpen, color: "#64748b", bgColor: "#f8fafc" },
};

function formatDocType(type) {
  return (type || "other").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function SectionBadge({ sectionType }) {
  const meta = SECTION_META[sectionType] || SECTION_META.medical_record;
  const Icon = meta.icon;
  return (
    <span
      className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-md font-bold border"
      style={{
        backgroundColor: meta.bgColor,
        color: meta.color,
        borderColor: meta.color + "30",
      }}
    >
      <Icon className="w-2.5 h-2.5" />
      {meta.label}
    </span>
  );
}

function VisitCard({ visit, color, onGoTo, onEdit, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const sectionType = visit.section_type || "medical_record";
  const meta = SECTION_META[sectionType] || SECTION_META.medical_record;
  const isMedical = sectionType === "medical_record" || sectionType === "medical_bill";

  return (
    <div
      className="bg-white border rounded-xl px-4 py-3 text-sm shadow-sm hover:shadow-md transition-all duration-300"
      style={{ borderLeftWidth: "4px", borderLeftColor: meta.color, borderTopColor: "#e2e8f0", borderRightColor: "#e2e8f0", borderBottomColor: "#e2e8f0" }}
    >
      {/* Header row */}
      <button 
        onClick={() => setExpanded(!expanded)} 
        className="w-full flex items-center justify-between group focus:outline-none"
      >
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-full bg-slate-50 flex items-center justify-center border border-slate-200 text-slate-400 group-hover:bg-slate-100 group-hover:text-primary-500 transition-colors">
            <ChevronRight className={`w-3.5 h-3.5 transition-transform duration-300 ${expanded ? 'rotate-90' : ''}`} />
          </div>
          <div className="font-semibold text-slate-800 tracking-tight text-left text-xs">
            <span className="opacity-90">Pg</span> {visit.start_page}–{visit.end_page}
            {isMedical && visit.date_of_service && (
              <span className="text-slate-500 font-medium text-[11px] ml-2.5 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 uppercase tracking-wide">
                {visit.date_of_service}
              </span>
            )}
          </div>
        </div>
        <SectionBadge sectionType={sectionType} />
      </button>

      {/* Expandable Details */}
      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${expanded ? 'max-h-96 opacity-100 mt-3' : 'max-h-0 opacity-0 mt-0 pointer-events-none'}`}>
        <div className="text-xs text-slate-600 space-y-2 bg-slate-50/60 p-3 rounded-lg border border-slate-100 mb-3">
          {isMedical && visit.date_of_service && (
            <p className="flex justify-between items-center">
              <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Date of Service</span>
              <span className="font-semibold text-slate-700">{visit.date_of_service}</span>
            </p>
          )}
          {isMedical && visit.facility_name && (
            <p className="flex justify-between items-center">
              <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Facility</span>
              <span className="font-semibold text-slate-700 truncate ml-2 text-right">{visit.facility_name}</span>
            </p>
          )}
          {isMedical && visit.provider_name && (
            <p className="flex justify-between items-center">
              <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Provider</span>
              <span className="font-semibold text-slate-700 truncate ml-2 text-right">{visit.provider_name}</span>
            </p>
          )}
          {isMedical && visit.document_type && (
            <p className="flex justify-between items-center">
              <span className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">Doc Type</span>
              <span className="font-semibold text-slate-700">{formatDocType(visit.document_type)}</span>
            </p>
          )}
          {visit.notes && (
            <p className="italic text-slate-500 mt-2.5 pt-2.5 border-t border-slate-200">
              "{visit.notes}"
            </p>
          )}
          {!isMedical && !visit.notes && (
            <p className="text-slate-400 italic text-center py-1">No additional details.</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onGoTo(visit.start_page)}
            className="flex-1 justify-center items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-2.5 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 transition-colors flex shadow-sm"
            title="Go to first page of this visit"
          >
            <Eye className="w-3.5 h-3.5" /> View
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => onEdit(visit)}
              className="flex justify-center items-center gap-1 text-[10px] uppercase tracking-wider font-bold px-3 py-2 bg-primary-50 hover:bg-primary-100 rounded-lg text-primary-700 transition-colors shadow-sm"
            >
              <Edit2 className="w-3.5 h-3.5" /> Edit
            </button>
            <button
              onClick={() => {
                if (window.confirm("Delete this visit annotation?")) {
                  onDelete(visit.id);
                }
              }}
              className="flex justify-center items-center text-xs font-semibold px-3 py-2 bg-red-50 hover:bg-red-100 rounded-lg text-red-600 transition-colors shadow-sm"
              title="Delete Visit"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function VisitList({
  visits,
  colors,
  onGoTo,
  onEdit,
  onDelete,
}) {
  if (visits.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400 text-sm">
        <p className="text-base">No visits annotated yet.</p>
        <p className="mt-2">
          Navigate pages and add visits using the form above.
        </p>
      </div>
    );
  }

  // Group visits by section_type for visual grouping
  const grouped = {};
  const sectionOrder = ["injury_photo", "vehicle_photo", "medical_record", "medical_bill", "other"];
  
  visits.forEach((v) => {
    const sec = v.section_type || "medical_record";
    if (!grouped[sec]) grouped[sec] = [];
    grouped[sec].push(v);
  });

  return (
    <div className="pt-2">
      <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider flex items-center gap-2 mb-3">
        <ListIcon className="w-4 h-4 text-slate-400" /> Visits <span className="text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded-full text-[10px]">{visits.length}</span>
      </h3>
      <div className="space-y-2.5">
        {sectionOrder.map((sec) => {
          const secVisits = grouped[sec];
          if (!secVisits || secVisits.length === 0) return null;
          const meta = SECTION_META[sec] || SECTION_META.medical_record;
          return (
            <div key={sec}>
              <div className="flex items-center gap-2 mb-1.5 mt-2">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
                <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: meta.color }}>
                  {meta.label}s ({secVisits.length})
                </span>
              </div>
              {secVisits.map((visit, idx) => (
                <div key={visit.id} className="mb-2">
                  <VisitCard
                    visit={visit}
                    color={meta.color}
                    onGoTo={onGoTo}
                    onEdit={onEdit}
                    onDelete={onDelete}
                  />
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}