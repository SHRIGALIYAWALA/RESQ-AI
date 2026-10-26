"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

interface BuildingPin {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  distance_m?: number;
}

interface BuildingMapProps {
  center?: [number, number];
  buildings?: BuildingPin[];
  height?: string;
}

function MapInner({ center = [28.6139, 77.209], buildings = [], height = "280px" }: BuildingMapProps) {
  const [leaflet, setLeaflet] = useState<typeof import("leaflet") | null>(null);
  const [reactLeaflet, setReactLeaflet] = useState<typeof import("react-leaflet") | null>(null);

  useEffect(() => {
    Promise.all([import("leaflet"), import("react-leaflet")]).then(([L, RL]) => {
      // Fix default marker icons in Next.js
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });
      setLeaflet(L);
      setReactLeaflet(RL);
    });
  }, []);

  if (!leaflet || !reactLeaflet) {
    return <div style={{ height }} className="flex items-center justify-center rounded border border-cyan-500/20 bg-black/40 text-xs text-muted">Loading map...</div>;
  }

  const { MapContainer, TileLayer, Marker, Popup, Circle } = reactLeaflet;

  return (
    <div style={{ height }} className="overflow-hidden rounded-lg border border-cyan-500/20">
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <MapContainer center={center} zoom={14} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Circle center={center} radius={500} pathOptions={{ color: "#00f3ff", fillColor: "#00f3ff", fillOpacity: 0.08 }} />
        {buildings.map((b) => (
          <Marker key={b.id} position={[b.latitude, b.longitude]}>
            <Popup>
              <strong>{b.name}</strong>
              {b.distance_m != null && <div>{b.distance_m}m away</div>}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

export const BuildingMap = dynamic(() => Promise.resolve(MapInner), { ssr: false });
