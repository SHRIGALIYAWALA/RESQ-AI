export interface Camera {
  id: number;
  name: string;
  zone: string;
  status: string;
  fps?: number;
  reconnect_attempts?: number;
  last_error?: string | null;
  people_count?: number;
  hazards?: Array<{ type: string; severity?: string }>;
}

export interface Incident {
  id: number;
  title: string;
  incident_type: string;
  severity: string;
  status: string;
  building_id?: number;
  location?: Record<string, unknown>;
  created_at?: string;
}

export interface Announcement {
  id: number;
  message?: string;
  text_en?: string;
  status: string;
  language?: string;
}

export interface DashboardData {
  system_status: string;
  active_incidents: number;
  buildings: Array<{ id: number; name: string }>;
  incidents: Incident[];
  resources?: Array<{ id: number; name: string; resource_type: string; status: string }>;
  routes?: Array<{ id: number; name: string; status: string; risk?: number }>;
  mode?: string;
}

export interface WsEvent {
  event: string;
  [key: string]: unknown;
}
