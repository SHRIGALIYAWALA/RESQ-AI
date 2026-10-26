import type { Incident } from "@/types";

interface IncidentListProps {
  incidents: Incident[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function IncidentList({ incidents, selectedId, onSelect }: IncidentListProps) {
  if (incidents.length === 0) {
    return <p className="p-4 text-sm text-muted">No active incidents. System standing by.</p>;
  }

  return (
    <div className="space-y-2">
      {incidents.map((inc) => {
        const isCritical = inc.severity === "critical" || inc.severity === "high";
        const isSelected = inc.id === selectedId;
        return (
          <button
            key={inc.id}
            type="button"
            onClick={() => onSelect(inc.id)}
            className={`w-full rounded-lg border p-3 text-left transition ${
              isSelected
                ? "border-cyan-400/60 bg-cyan-400/10"
                : "border-white/10 bg-card hover:border-cyan-400/30"
            } ${isCritical ? "shadow-[0_0_12px_rgba(255,0,85,0.25)]" : ""}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm">{inc.title}</span>
              <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${
                inc.severity === "critical" ? "border-danger text-danger" : "border-warning text-warning"
              }`}>
                {inc.severity.toUpperCase()}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted">{inc.incident_type} · {inc.status}</p>
          </button>
        );
      })}
    </div>
  );
}
