import type { Announcement, Camera, DashboardData, Incident } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: init?.credentials || "include" });
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await apiFetch(path, { ...init, headers });
  if (!response.ok) {
    throw new Error(`API ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getDashboard: () => fetchJson<DashboardData>("/api/dashboard"),
  getCameras: () => fetchJson<Camera[]>("/api/cameras"),
  getIncidents: () => fetchJson<Incident[]>("/api/incidents"),
  getIncident: (id: number) => fetchJson<Record<string, unknown>>(`/api/incidents/${id}`),
  analyzeIncident: (id: number) => fetchJson<{ analysis: Record<string, unknown> }>(`/api/incidents/${id}/analyze`, { method: "POST" }),
  generateAnnouncement: (text: string, buildingId: number) => fetchJson<Announcement>("/api/announcements/generate", {
    method: "POST",
    body: JSON.stringify({ text_en: text, building_id: buildingId }),
  }),
  approveAnnouncement: (id: number) => fetchJson<{ announcement: Announcement }>(`/api/announcements/${id}/approve`, { method: "POST" }),
  getAnnouncements: () => fetchJson<Announcement[]>("/api/announcements"),
  getBuildingGraph: (buildingId: number) => fetchJson<Record<string, unknown>>(`/api/buildings/${buildingId}/graph`),
};
