"use client";

import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { CameraGrid } from "@/components/CameraGrid";
import { IncidentList } from "@/components/IncidentList";
import { AIRecommendation } from "@/components/AIRecommendation";
import { DigitalTwin } from "@/components/DigitalTwin";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/services/api";
import type { Announcement, Camera, DashboardData, Incident, WsEvent } from "@/types";

interface GraphNode { id: string; node_type?: string; floor_number?: number; status?: string; risk_score?: number; occupancy?: number; }
interface GraphEdge { source: string; target: string; status?: string; distance_m?: number; }
interface GraphData { nodes: GraphNode[]; edges: GraphEdge[]; }

export default function CommandCenter() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [announcementBusy, setAnnouncementBusy] = useState(false);
  const [approvingAnnouncementId, setApprovingAnnouncementId] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");
  const pendingAnnouncementCount = announcements.filter((item) => item.status === "PENDING_OPERATOR_APPROVAL").length;

  const loadData = useCallback(async () => {
    try {
      const [dashboardData, camData, incData, annData] = await Promise.all([
        api.getDashboard(),
        api.getCameras(),
        api.getIncidents(),
        api.getAnnouncements(),
      ]);
      setDashboard(dashboardData);
      setCameras(camData);
      setIncidents(incData);
      setAnnouncements(annData);
      setLoadError(false);
      if (!selectedId && incData.length > 0) {
        setSelectedId(incData[0].id);
      }
    } catch (err) {
      console.warn("Dashboard load error:", err);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    const buildingId = dashboard?.buildings[0]?.id;
    if (!buildingId) return;
    api.getBuildingGraph(buildingId).then((data) => {
      setGraph({
        nodes: Array.isArray(data.nodes) ? data.nodes as GraphNode[] : [],
        edges: Array.isArray(data.edges) ? data.edges as GraphEdge[] : [],
      });
    }).catch(() => setGraph({ nodes: [], edges: [] }));
  }, [dashboard]);

  const loadIncident = useCallback(async (id: number) => {
    try {
      const data = await api.getIncident(id);
      setAnalysis((data.analysis as Record<string, unknown>) || null);
    } catch {
      setAnalysis(null);
    }
  }, []);

  const handleWsEvent = useCallback((event: WsEvent) => {
    if (["new_incident", "incident_reanalyzed", "occupants_notified", "building_vision_update", "vision_update"].includes(event.event)) {
      loadData();
    }
    if (event.event === "hazard_detected" || event.event === "danger_zone_update") {
      loadData();
    }
  }, [loadData]);

  const { connected } = useWebSocket(handleWsEvent);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { if (selectedId) loadIncident(selectedId); }, [selectedId, loadIncident]);

  const selectedIncident = incidents.find((incident) => incident.id === selectedId);
  const decision = analysis?.decision as Record<string, unknown> | undefined;
  const evacuation = analysis?.evacuation_plan as Record<string, unknown> | undefined;
  const communication = (analysis?.communication || analysis?.communications) as Record<string, unknown> | undefined;
  const incidentClassification = analysis?.incident_classification as Record<string, unknown> | undefined;
  const classification = incidentClassification?.classification as Record<string, unknown> | undefined;
  const recommendedActions = Array.isArray(classification?.recommended_actions)
    ? classification.recommended_actions
    : [];
  const recommendation = String(
    decision?.recommended_action ||
    evacuation?.primary_action ||
    communication?.announcement_script_en ||
    communication?.citizen_alert ||
    recommendedActions[0] ||
    "",
  ).trim();

  const runAnalysis = async () => {
    if (!selectedId) return;
    setAnalysisBusy(true);
    setActionError("");
    try {
      const result = await api.analyzeIncident(selectedId);
      setAnalysis(result.analysis);
    } catch {
      setActionError("Could not analyze this incident. Check your sign-in and backend logs, then try again.");
    } finally {
      setAnalysisBusy(false);
    }
  };

  const createAnnouncement = async () => {
    const buildingId = selectedIncident?.building_id ?? dashboard?.buildings[0]?.id;
    if (!recommendation || !buildingId) return;
    setAnnouncementBusy(true);
    setActionError("");
    try {
      const announcement = await api.generateAnnouncement(recommendation, buildingId);
      setAnnouncements((current) => [...current, announcement]);
    } catch {
      setActionError("Could not generate the announcement. An authorized dispatcher may be required.");
    } finally {
      setAnnouncementBusy(false);
    }
  };

  const approveAnnouncement = async (id: number) => {
    const approved = window.confirm("Approve and broadcast this announcement to occupants?");
    if (!approved) return;
    setApprovingAnnouncementId(id);
    setActionError("");
    try {
      const result = await api.approveAnnouncement(id);
      setAnnouncements((current) =>
        current.map((item) => item.id === id ? result.announcement : item),
      );
    } catch {
      setActionError("Could not approve the announcement. Check dispatcher authorization and backend logs.");
    } finally {
      setApprovingAnnouncementId(null);
    }
  };

  return (
    <div className="min-h-screen">
      <Header wsConnected={connected} />
      <main className="mx-auto max-w-[1800px] space-y-4 p-4 md:p-5">
        <section className="sci-panel grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <StatusItem label="SYSTEM" value={dashboard?.system_status?.toUpperCase() || (loading ? "LOADING" : "UNAVAILABLE")} tone={dashboard?.system_status === "online" ? "text-safe" : "text-warning"} />
          <StatusItem label="ACTIVE INCIDENT" value={selectedIncident ? selectedIncident.incident_type.toUpperCase() : "NONE"} tone={selectedIncident ? "text-danger" : "text-muted"} />
          <StatusItem label="SEVERITY" value={selectedIncident?.severity?.toUpperCase() || "STANDBY"} tone={selectedIncident ? "text-warning" : "text-muted"} />
          <StatusItem label="LOCATION" value={selectedIncident?.location ? formatLocation(selectedIncident.location) : dashboard?.buildings[0]?.name || "NO FACILITY"} tone="text-cyan-300" />
          <StatusItem label="INCIDENT ID" value={selectedIncident ? `INC-${String(selectedIncident.id).padStart(4, "0")}` : "--"} tone="text-cyan-300" />
        </section>
        {loadError && <div className="border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger" role="alert">Operational data is unavailable. Live values will appear when the API reconnects.</div>}
        <div className="grid min-h-[calc(100vh-190px)] grid-cols-1 gap-4 xl:h-[calc(100vh-190px)] xl:min-h-0 xl:grid-cols-[340px_minmax(440px,1fr)_380px]">
        {/* Left: Cameras + Incidents */}
        <section className="sci-panel flex min-h-0 flex-col gap-4 overflow-y-auto">
          <PanelHeader title="📡 LIVE CAMERA GRID" />
          <CameraGrid cameras={cameras} />
          <PanelHeader title="🚨 Active Incidents" />
          <IncidentList
            incidents={incidents}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </section>

        {/* Center: live operational status */}
        <section className="sci-panel flex min-h-0 flex-col gap-4 overflow-y-auto">
          <PanelHeader title="⚡ DIGITAL TWIN // OPERATIONAL PULSE" />
          {graph.nodes.length > 0 ? (
            <DigitalTwin floor={Number(graph.nodes[0].floor_number || 1)} nodes={graph.nodes} edges={graph.edges} />
          ) : (
            <div className="flex min-h-[260px] items-center justify-center border border-white/10 bg-black/20 p-6 text-center text-sm text-muted">{loading ? "Loading building structure..." : "No building graph data available."}</div>
          )}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-2">
            <Metric label="Active incidents" value={dashboard ? String(incidents.filter((item) => item.status === "open").length) : "--"} tone="text-danger" />
            <Metric label="Camera feeds" value={dashboard ? String(cameras.length) : "--"} tone="text-cyan-300" />
            <Metric label="Tracked people" value={dashboard ? String(cameras.reduce((sum, camera) => sum + (camera.people_count ?? 0), 0)) : "--"} tone="text-safe" />
            <Metric label="Pending broadcasts" value={dashboard ? String(pendingAnnouncementCount) : "--"} tone="text-warning" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <DataStrip label="RESOURCES" value={dashboard?.resources?.length != null ? String(dashboard.resources.length) : "UNAVAILABLE"} />
            <DataStrip label="ROUTES" value={dashboard?.routes?.length != null ? String(dashboard.routes.length) : "UNAVAILABLE"} />
          </div>
        </section>

        {/* Right: AI + Announcements */}
        <section className="sci-panel flex min-h-0 flex-col gap-4 overflow-y-auto">
          <PanelHeader title="🧠 AI Decision Panel" />
          <AIRecommendation analysis={analysis} />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded border border-cyan-400/40 px-3 py-2 text-xs text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={runAnalysis}
              disabled={!selectedId || analysisBusy}
            >
              {analysisBusy ? "Analyzing..." : "Analyze selected incident"}
            </button>
            <button
              type="button"
              className="rounded border border-purple-400/40 px-3 py-2 text-xs text-purple-200 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={createAnnouncement}
              disabled={!recommendation || announcementBusy}
            >
              {announcementBusy ? "Generating..." : "Generate announcement"}
            </button>
          </div>
          {actionError && <p className="text-xs text-danger" role="alert">{actionError}</p>}
          <PanelHeader title="📢 Announcements" />
          <div className="space-y-2">
            {announcements.length === 0 ? (
              <p className="text-sm text-muted">No announcements have been generated.</p>
            ) : (
              announcements.map((ann) => (
                <div key={ann.id} className="rounded border border-white/10 bg-card p-2 text-xs">
                  <span className="font-mono text-cyan-400">{ann.status}</span>
                  <p className="mt-1">{ann.message || ann.text_en || "Announcement text unavailable."}</p>
                  {ann.status === "PENDING_OPERATOR_APPROVAL" && (
                    <button
                      type="button"
                      className="mt-2 rounded border border-warning/40 px-2 py-1 text-warning disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => approveAnnouncement(ann.id)}
                      disabled={approvingAnnouncementId !== null}
                    >
                      {approvingAnnouncementId === ann.id ? "Approving..." : "Approve & broadcast"}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
        </div>
      </main>
    </div>
  );
}

function formatLocation(location: Record<string, unknown>) {
  return String(location.room || location.floor || location.zone || "ACTIVE SITE").toUpperCase();
}

function StatusItem({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className="border-l-2 border-cyan-500/30 pl-3 first:border-l-0 md:first:border-l-2"><p className="font-mono text-[10px] tracking-widest text-muted">{label}</p><strong className={`mt-1 block truncate text-sm ${tone}`}>{value}</strong></div>;
}

function DataStrip({ label, value }: { label: string; value: string }) {
  return <div className="border border-white/10 bg-black/20 p-3"><p className="font-mono text-[10px] text-cyan-400">{label}</p><strong className="mt-1 block text-sm text-white">{value}</strong></div>;
}

function PanelHeader({ title, actionLabel, actionHref }: { title: string; actionLabel?: string; actionHref?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
      <span className="font-mono text-sm font-bold tracking-wider text-cyan-400">{title}</span>
      {actionLabel && actionHref && (
        <a href={actionHref} className="rounded border border-cyan-400/50 bg-cyan-400/10 px-2.5 py-1 text-xs font-semibold text-cyan-400 hover:bg-cyan-400/20">
          {actionLabel}
        </a>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className="border border-white/10 bg-black/20 p-3"><p className="text-xs text-muted">{label}</p><strong className={`mt-1 block text-2xl font-bold ${tone}`}>{value}</strong></div>;
}
