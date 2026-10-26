"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { BuildingMap } from "@/components/BuildingMap";
import { DigitalTwin } from "@/components/DigitalTwin";
import { apiFetch } from "@/services/api";

interface BuildingSummary { id: number; name: string; address: string; latitude?: number; longitude?: number; floors_count: number; rooms_count: number; }
interface GraphNode { id: string; node_type?: string; floor_number?: number; status?: string; risk_score?: number; occupancy?: number; }
interface GraphEdge { source: string; target: string; status?: string; distance_m?: number; }
interface GraphData { nodes: GraphNode[]; edges: GraphEdge[]; }

export default function BuildingsPage() {
  const [buildings, setBuildings] = useState<BuildingSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [floor, setFloor] = useState(1);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/buildings").then((res) => res.json()).then((data: BuildingSummary[]) => {
      setBuildings(data);
      if (data[0]) setSelectedId(data[0].id);
    }).catch(() => setError("Building data is unavailable."));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    apiFetch(`/api/buildings/${selectedId}/graph`).then((res) => res.json()).then((data: GraphData) => {
      setGraph(data);
      const floors = data.nodes.map((node) => Number(node.floor_number || 1));
      setFloor(Math.min(...floors, 1));
    }).catch(() => setError("This building has no graph data yet."));
  }, [selectedId]);

  const selected = buildings.find((building) => building.id === selectedId);
  const floors = Array.from(new Set(graph.nodes.map((node) => Number(node.floor_number || 1)))).sort((a, b) => a - b);
  const floorEdges = graph.edges.filter((edge) => graph.nodes.some((node) => node.id === edge.source && Number(node.floor_number || 1) === floor));

  return <div className="min-h-screen">
    <Header wsConnected={false} />
    <main className="mx-auto max-w-[1500px] space-y-4 p-4 md:p-6">
      <section className="sci-panel flex flex-wrap items-end justify-between gap-4">
        <div><p className="font-mono text-xs tracking-widest text-cyan-400">STRUCTURE INTELLIGENCE</p><h1 className="mt-1 text-2xl font-bold text-white">Digital Twin</h1><p className="mt-1 text-sm text-muted">Rooms, corridors, exits and evacuation connections from the registered building model.</p></div>
        <label className="text-xs text-muted">Facility<select className="mt-1 block min-w-64 rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white" value={selectedId ?? ""} onChange={(event) => setSelectedId(Number(event.target.value))}><option value="">Select a building</option>{buildings.map((building) => <option key={building.id} value={building.id}>{building.name} · {building.address}</option>)}</select></label>
      </section>
      {error && <p className="text-sm text-danger">{error}</p>}
      {selected ? <>
        <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="sci-panel"><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-mono text-sm font-bold text-cyan-400">{selected.name}{" // "}Evacuation Flow</h2><p className="text-xs text-muted">{selected.address} · {graph.nodes.length} mapped elements · {graph.edges.length} connections</p></div><div className="flex gap-1">{floors.map((value) => <button key={value} type="button" onClick={() => setFloor(value)} className={`rounded border px-3 py-1 font-mono text-xs ${floor === value ? "border-cyan-400 bg-cyan-400/20 text-cyan-300" : "border-white/20 text-muted"}`}>F{value}</button>)}</div></div><DigitalTwin floor={floor} nodes={graph.nodes} edges={graph.edges} /></div>
          <div className="space-y-4"><div className="sci-panel"><h2 className="mb-3 font-mono text-sm font-bold text-cyan-400">LEGEND</h2><div className="grid grid-cols-2 gap-2 text-xs"><span className="border-l-4 border-safe bg-safe/10 p-2 text-safe">SAFE / EXIT</span><span className="border-l-4 border-warning bg-warning/10 p-2 text-warning">ELEVATED</span><span className="border-l-4 border-danger bg-danger/10 p-2 text-danger">DANGER</span><span className="border-l-4 border-cyan-400 bg-cyan-400/10 p-2 text-cyan-200">STRUCTURE</span></div></div><div className="sci-panel"><h2 className="mb-3 font-mono text-sm font-bold text-cyan-400">PATH CONNECTIONS</h2><div className="max-h-64 space-y-2 overflow-y-auto text-xs">{floorEdges.map((edge, index) => <div key={`${edge.source}-${edge.target}-${index}`} className="flex justify-between border-b border-white/10 pb-2"><span>{edge.source} → {edge.target}</span><span className={edge.status === "blocked" ? "text-danger" : "text-safe"}>{edge.status || "available"}</span></div>)}</div></div></div>
        </section>
        <section className="sci-panel"><h2 className="mb-2 font-mono text-xs text-cyan-400">GIS LOCATION</h2><BuildingMap center={[selected.latitude ?? 28.6139, selected.longitude ?? 77.209]} buildings={selected.latitude != null && selected.longitude != null ? [{ id: selected.id, name: selected.name, latitude: selected.latitude, longitude: selected.longitude }] : []} height="360px" /></section>
      </> : <section className="sci-panel py-16 text-center text-sm text-muted">No registered building selected.</section>}
    </main>
  </div>;
}
