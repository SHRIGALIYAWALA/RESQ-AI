"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { apiFetch } from "@/services/api";

export default function IncidentReportPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [capturedImage, setCapturedImage] = useState<File | null>(null);
  const [cameraError, setCameraError] = useState("");
  const [form, setForm] = useState({
    title: "",
    incident_type: "fire",
    severity: "high",
    location: "",
    description: "",
    building_id: "1",
  });
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = cameraStream;
    }
    return () => cameraStream?.getTracks().forEach((track) => track.stop());
  }, [cameraStream]);

  const startCamera = async () => {
    setCameraError("");
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera access requires HTTPS and a supported browser.");
      }
      setCameraStream(await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      }));
    } catch (err) {
      setCameraError(err instanceof Error ? err.message : "Camera permission was not granted.");
    }
  };

  const captureImage = async () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError("The camera preview is not ready yet.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Could not capture an image from the camera preview.");
      return;
    }
    context.drawImage(video, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
    if (!blob) {
      setCameraError("Could not encode the captured image.");
      return;
    }
    setCapturedImage(new File([blob], `incident-${Date.now()}.jpg`, { type: "image/jpeg" }));
    setCameraError("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const floorMatch = form.location.match(/floor\s*(\d+)/i);
    const roomMatch = form.location.match(/room\s*(\w+)/i);

    const payload = {
      title: form.title,
      incident_type: form.incident_type,
      severity: form.severity,
      description: form.description,
      building_id: parseInt(form.building_id) || undefined,
      location: {
        room: roomMatch?.[1] || form.location,
        floor: floorMatch ? parseInt(floorMatch[1]) : 1,
        raw: form.location,
      },
    };

    try {
      const res = await apiFetch("/api/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        setResult(data);
        if (capturedImage) {
          const evidence = new FormData();
          evidence.append("file", capturedImage);
          const mediaResponse = await apiFetch(`/api/incidents/${data.id}/media`, {
            method: "POST",
            body: evidence,
          });
          if (!mediaResponse.ok) {
            const mediaError = await mediaResponse.json();
            setError(mediaError.detail || `Image upload failed with status ${mediaResponse.status}`);
            return;
          }
        }
      } else {
        setError(data.detail || `Failed with status ${res.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header wsConnected={false} />
      <main className="mx-auto max-w-2xl p-6">
        <div className="sci-panel">
          <h1 className="mb-4 font-mono text-sm font-bold text-cyan-400">🚨 Real-Time Emergency Report</h1>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs text-muted">Incident Title</label>
              <input required className="mt-1 w-full rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white"
                value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Fire observed in 2nd Floor Server Room" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted">Incident Type</label>
                <select className="mt-1 w-full rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white"
                  value={form.incident_type} onChange={(e) => setForm({ ...form, incident_type: e.target.value })}>
                  <option value="fire">🔥 Fire</option>
                  <option value="smoke">💨 Smoke</option>
                  <option value="medical">🩺 Medical</option>
                  <option value="hazmat">☣️ Hazmat</option>
                  <option value="blocked_path">🚫 Blocked Path</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted">Severity</label>
                <select className="mt-1 w-full rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white"
                  value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                  <option value="critical">CRITICAL</option>
                  <option value="high">HIGH</option>
                  <option value="medium">MEDIUM</option>
                  <option value="low">LOW</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted">Location / Room / Floor</label>
              <input required className="mt-1 w-full rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white"
                value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="Floor 2, Room 202" />
            </div>
            <div>
              <label className="text-xs text-muted">Description</label>
              <textarea rows={4} className="mt-1 w-full rounded border border-cyan-500/30 bg-black px-3 py-2 text-sm text-white"
                value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Describe what you see, people trapped, smoke density..." />
            </div>
            <section className="space-y-3 rounded border border-cyan-500/20 p-3">
              <div className="flex flex-wrap gap-2">
                {!cameraStream ? (
                  <button type="button" onClick={startCamera} className="rounded border border-cyan-500/40 px-3 py-2 text-xs text-cyan-300">
                    Enable phone camera
                  </button>
                ) : (
                  <>
                    <button type="button" onClick={captureImage} className="rounded border border-cyan-500/40 px-3 py-2 text-xs text-cyan-300">
                      Capture incident photo
                    </button>
                    <button type="button" onClick={() => { cameraStream.getTracks().forEach((track) => track.stop()); setCameraStream(null); }} className="rounded border border-white/20 px-3 py-2 text-xs text-muted">
                      Stop camera
                    </button>
                  </>
                )}
              </div>
              {cameraStream && <video ref={videoRef} autoPlay playsInline muted className="max-h-72 w-full rounded bg-black object-contain" aria-label="Phone camera preview" />}
              {capturedImage && <p className="text-xs text-safe">Photo ready to attach to this incident: {capturedImage.name}</p>}
              {cameraError && <p role="alert" className="text-xs text-danger">{cameraError}</p>}
              <p className="text-xs text-muted">Camera evidence is retained with the incident until an authorized operator deletes it. Camera access requires HTTPS.</p>
            </section>
            <button type="submit" disabled={loading}
              className="w-full rounded border border-danger bg-danger/20 py-3 text-sm font-bold tracking-widest text-danger disabled:opacity-50">
              {loading ? "TRANSMITTING..." : "🚨 TRANSMIT EMERGENCY REPORT"}
            </button>
          </form>

          {error && <p className="mt-4 text-sm text-danger">{error}</p>}
          {result && (
            <div className="mt-4 rounded-lg border border-safe/30 bg-safe/5 p-4">
              <p className="font-bold text-safe">✓ Emergency Report Transmitted</p>
              <p className="mt-2 text-sm">Incident ID: <strong>#{String(result.id)}</strong></p>
              <p className="text-xs text-muted mt-1">Multi-agent analysis complete. Human approval required for broadcasts.</p>
              <Link href="/" className="mt-3 inline-block text-xs text-cyan-400 hover:underline">Return to Command Center →</Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
