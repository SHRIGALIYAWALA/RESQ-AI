"use client";

import { useEffect, useRef, useState } from "react";
import type { Camera } from "@/types";

const CAMERA_API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface CameraGridProps {
  cameras: Camera[];
}

function CameraCard({ camera }: { camera: Camera }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [useSnapshot, setUseSnapshot] = useState(false);
  const streamUrl = `${CAMERA_API_BASE}/api/cameras/${camera.id}/stream`;
  const snapshotUrl = `${CAMERA_API_BASE}/api/cameras/${camera.id}/snapshot`;
  const hasHazard = (camera.hazards?.length ?? 0) > 0;
  const isOnline = camera.status.toLowerCase() === "online";

  useEffect(() => {
    const element = cardRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting);
      if (entry.isIntersecting) setUseSnapshot(false);
    }, { rootMargin: "160px" });

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={cardRef} className="overflow-hidden rounded-lg border border-cyan-500/20 bg-card">
      <div className="flex justify-between px-3 py-1.5 font-mono text-xs">
        <span className="text-cyan-400">{camera.name} ({camera.zone})</span>
        <span className={isOnline ? "text-safe" : "text-warning"}>
          ● {camera.status.toUpperCase()} | {camera.fps != null && camera.fps > 0 ? `${camera.fps.toFixed(1)} FPS` : "FPS N/A"}
        </span>
      </div>
      <div className="relative h-36 bg-black">
        {isVisible ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              className="h-full w-full object-cover"
              src={useSnapshot ? snapshotUrl : streamUrl}
              alt={camera.name}
              onError={() => setUseSnapshot(true)}
            />
            {useSnapshot && <span className="absolute bottom-1 left-1 rounded bg-black/75 px-2 py-1 text-[10px] text-warning">LIVE STREAM UNAVAILABLE · LATEST FRAME</span>}
          </>
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-xs text-muted">
            CAMERA FEED PAUSED
          </div>
        )}
      </div>
      {camera.last_error && (
        <p className="border-t border-danger/20 bg-danger/5 px-3 py-2 text-xs text-warning">
          Feed unavailable: {camera.last_error}
          {camera.reconnect_attempts ? ` · retry ${camera.reconnect_attempts}` : ""}
        </p>
      )}
      <div className="flex justify-between bg-panel/90 px-3 py-1.5 text-xs">
        <span>PEOPLE: <strong>{camera.people_count != null ? camera.people_count : "N/A"}</strong></span>
        <span className={`font-bold ${hasHazard ? "text-danger" : "text-safe"}`}>
          {hasHazard ? `🚨 ${camera.hazards![0].type.toUpperCase()}` : camera.hazards ? "✓ CLEAR" : "HAZARD N/A"}
        </span>
      </div>
    </div>
  );
}

export function CameraGrid({ cameras }: CameraGridProps) {
  if (cameras.length === 0) {
    return (
      <p className="p-5 text-sm text-muted">
        No cameras registered. Register a webcam or RTSP stream to view live feeds.
      </p>
    );
  }

  const orderedCameras = [...cameras].sort((left, right) => {
    const leftIsPhone = /android|mobile|phone/i.test(`${left.name} ${left.zone}`);
    const rightIsPhone = /android|mobile|phone/i.test(`${right.name} ${right.zone}`);
    return Number(rightIsPhone) - Number(leftIsPhone) || left.id - right.id;
  });

  return (
    <div className="grid gap-3">
      {orderedCameras.map((camera) => <CameraCard key={camera.id} camera={camera} />)}
    </div>
  );
}
