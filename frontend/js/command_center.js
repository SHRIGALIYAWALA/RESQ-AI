document.addEventListener("DOMContentLoaded", () => {
  const twin = new BuildingDigitalTwin("twinCanvas");
  window.resqWS.connect();

  let activeIncidentId = null;
  let currentBuildingId = 1;

  // Floor switcher
  document.querySelectorAll(".floor-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".floor-btn").forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      const floor = e.target.getAttribute("data-floor");
      twin.setFloor(floor);
    });
  });

  // Load Initial Data
  async function loadInitialData() {
    try {
      // 1. Fetch Cameras
      const camRes = await fetch("/api/cameras");
      if (camRes.ok) {
        const cameras = await camRes.json();
        renderCameras(cameras);
      }

      // 2. Fetch Incidents
      const incRes = await fetch("/api/incidents");
      if (incRes.ok) {
        const incidents = await incRes.json();
        renderIncidents(incidents);
        if (incidents.length > 0) {
          selectIncident(incidents[0].id);
        }
      }

      // 3. Fetch Announcements
      const annRes = await fetch("/api/announcements");
      if (annRes.ok) {
        const announcements = await annRes.json();
        renderAnnouncements(announcements);
      }
    } catch (err) {
      console.warn("Initial data load error:", err);
    }
  }

  // Render Camera Grid
  function renderCameras(cameras) {
    const grid = document.getElementById("cameraGrid");
    if (!grid) return;

    if (!cameras || cameras.length === 0) {
      grid.innerHTML = `<div style="padding: 20px; color: var(--text-muted); font-size: 0.85rem;">No cameras registered. Register a stream to view live feeds.</div>`;
      return;
    }

    grid.innerHTML = cameras
      .map(
        (cam) => `
      <div class="camera-feed-card">
        <div class="camera-feed-overlay">
          <span style="color: var(--border-cyan);">${cam.name} (${cam.zone})</span>
          <span style="color: ${cam.status === "online" ? "var(--safe-green)" : "var(--warning-amber)"};">
            ● ${cam.status.toUpperCase()} | ${cam.fps || 0} FPS
          </span>
        </div>
        <img class="camera-feed-img" src="/api/cameras/${cam.id}/stream" onerror="this.src='/api/cameras/${cam.id}/snapshot'" alt="${cam.name}">
        <div style="padding: 6px 10px; display: flex; justify-content: space-between; font-size: 0.75rem; background: rgba(13, 18, 31, 0.9);">
          <span>👥 Detected: <strong>${cam.people_count || 0}</strong></span>
          <span style="color: ${cam.hazards && cam.hazards.length > 0 ? "var(--danger-red)" : "var(--safe-green)"}; font-weight: bold;">
            ${cam.hazards && cam.hazards.length > 0 ? `🚨 ${cam.hazards[0].type.toUpperCase()}` : "✓ CLEAR"}
          </span>
        </div>
      </div>
    `
      )
      .join("");
  }

  // Render Incident List
  function renderIncidents(incidents) {
    const list = document.getElementById("incidentList");
    if (!list) return;

    if (!incidents || incidents.length === 0) {
      list.innerHTML = `<div style="padding: 15px; color: var(--text-muted); font-size: 0.85rem;">No active incidents. System standing by.</div>`;
      return;
    }

    list.innerHTML = incidents
      .map(
        (inc) => `
      <div class="agent-card ${inc.severity === "critical" || inc.severity === "high" ? "critical" : ""}" 
           style="cursor: pointer;" onclick="window.selectIncident(${inc.id})">
        <div class="agent-name" style="display: flex; justify-content: space-between;">
          <span>${inc.title}</span>
          <span class="brand-badge" style="color: ${inc.severity === "critical" ? "var(--danger-red)" : "var(--warning-amber)"};">
            ${inc.severity.toUpperCase()}
          </span>
        </div>
        <div class="agent-thought">Type: ${inc.incident_type} | Status: ${inc.status}</div>
      </div>
    `
      )
      .join("");
  }

  // Select Incident & Render Multi-Agent Thought Stream
  window.selectIncident = async function (incidentId) {
    activeIncidentId = incidentId;
    try {
      const res = await fetch(`/api/incidents/${incidentId}`);
      if (!res.ok) return;
      const data = await res.json();
      const analysis = data.analysis || {};

      // 1. Update Digital Twin
      const evac = analysis.evacuation_plan || {};
      twin.updateData(null, evac.danger_zones || [], evac.routes_by_room ? Object.values(evac.routes_by_room) : []);

      // 2. Render Agent Thought Stream
      renderAgentIntelligence(analysis);
      renderIncidentReviewPanel(data);
    } catch (err) {
      console.warn("Failed to select incident:", err);
    }
  };

  // Render Agent Intelligence Stream
  function renderAgentIntelligence(analysis) {
    const stream = document.getElementById("agentStream");
    if (!stream) return;

    const classification = analysis.incident_classification || {};
    const vision = analysis.vision_telemetry || {};
    const evac = analysis.evacuation_plan || {};
    const med = analysis.medical_triage || {};
    const res = analysis.resource_allocation || {};
    const comms = analysis.communications || {};

    stream.innerHTML = `
      <!-- Incident Agent -->
      <div class="agent-card">
        <div class="agent-name">🧠 INCIDENT AGENT</div>
        <div class="agent-thought">
          <strong>Type:</strong> ${classification.incident_type || "N/A"} | 
          <strong>Severity:</strong> ${classification.severity || "N/A"}<br>
          ${classification.summary || "Incident analysis standing by."}
        </div>
      </div>

      <!-- Vision Agent -->
      <div class="agent-card">
        <div class="agent-name">👁️ VISION AGENT</div>
        <div class="agent-thought">
          People Detected: <strong>${vision.total_people_detected || 0}</strong> across ${vision.cameras_online || 0} cameras.<br>
          Active Hazards: ${vision.active_hazards && vision.active_hazards.length > 0 ? vision.active_hazards.map((h) => h.type).join(", ") : "None reported."}
        </div>
      </div>

      <!-- Evacuation Agent -->
      <div class="agent-card">
        <div class="agent-name">🚪 EVACUATION AGENT (Dijkstra/A*)</div>
        <div class="agent-thought">
          Safe Exits: <strong style="color: var(--safe-green);">${(evac.primary_safe_exits || []).join(", ") || "None"}</strong><br>
          Blocked Exits: <strong style="color: var(--danger-red);">${(evac.blocked_exits || []).join(", ") || "None"}</strong><br>
          Rooms Routed: ${Object.keys(evac.room_instructions || {}).length}
        </div>
      </div>

      <!-- Medical Agent -->
      <div class="agent-card">
        <div class="agent-name">🩺 MEDICAL AGENT (START Triage)</div>
        <div class="agent-thought">
          Category: <strong>${med.triage_category || "Standard"}</strong> | Urgency: <strong>${med.urgency_level || "low"}</strong><br>
          AED Required: <strong>${med.aed_required ? "YES - DEPLOY IMMEDIATELY" : "No"}</strong>
        </div>
      </div>

      <!-- Resource Agent -->
      <div class="agent-card">
        <div class="agent-name">🚒 RESOURCE AGENT</div>
        <div class="agent-thought">
          Services: ${(res.required_services || []).join(", ")}<br>
          Staging: ${res.staging_area || "Main Entrance"}
        </div>
      </div>
    `;

    // Render Voice Announcement Bar if communication scripts exist
    if (comms.announcement_script_en) {
      renderAnnouncementPlayer(comms);
    }
  }

  // Render Announcement Player & Approval
  function renderAnnouncementPlayer(comms) {
    const container = document.getElementById("announcementSection");
    if (!container) return;

    container.innerHTML = `
      <div style="background: rgba(13, 18, 31, 0.95); border: 1px solid var(--border-cyan); border-radius: 6px; padding: 14px; margin-top: 10px;">
        <div style="font-size: 0.85rem; font-weight: bold; color: var(--border-cyan); margin-bottom: 8px;">
          📢 MULTILINGUAL VOICE BROADCAST (Human Authorization Required)
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 6px;">
          <strong>🇬🇧 EN:</strong> ${comms.announcement_script_en || ""}
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 6px;">
          <strong>🇮🇳 HI:</strong> ${comms.announcement_script_hi || ""}
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 12px;">
          <strong>🇮🇳 GU:</strong> ${comms.announcement_script_gu || ""}
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <button class="btn-approve" onclick="window.generateAndBroadcastAudio()">
            ✓ Authorize & Broadcast Audio
          </button>
          <span id="broadcastStatus" style="font-size: 0.8rem; color: var(--text-muted);">
            Standing by for operator authorization
          </span>
        </div>
      </div>
    `;
  }

  window.generateAndBroadcastAudio = async function () {
    const statusEl = document.getElementById("broadcastStatus");
    if (statusEl) statusEl.innerText = "Synthesizing multilingual audio...";

    try {
      const genRes = await fetch("/api/announcements/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          building_id: currentBuildingId,
          text_en: "Attention all occupants: please evacuate immediately via safe exits.",
          text_hi: "कृपया ध्यान दें: सभी लोग तुरंत सुरक्षित निकास से बाहर निकलें।",
          text_gu: "કૃપા કરીને ધ્યાન આપો: દરેક વ્યક્તિ તરત જ સુરક્ષિત બહાર નીકળો.",
        }),
      });

      if (genRes.ok) {
        const ann = await genRes.json();
        // Approve immediately
        const appRes = await fetch(`/api/announcements/${ann.id}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ operator: "Lead Safety Controller" }),
        });
        if (appRes.ok) {
          if (statusEl) {
            statusEl.innerHTML = `<span style="color: var(--safe-green); font-weight: bold;">✓ BROADCAST RELEASED</span>`;
          }
          // Play English audio
          if (ann.audio_en_url) {
            const audio = new Audio(ann.audio_en_url);
            audio.play().catch((e) => console.log("Audio autoplay prevented:", e));
          }
        }
      }
    } catch (err) {
      console.warn("Announcement broadcast failed:", err);
    }
  };

  function renderIncidentReviewPanel(incident) {
    const container = document.getElementById("reviewSection");
    if (!container) return;

    const reviewStatus = incident.review_status || "pending_review";
    const reviewDecision = incident.review_decision || "";
    const statusColor = reviewStatus === "reviewed" ? "var(--safe-green)" : "var(--warning-amber)";

    container.innerHTML = `
      <div style="background: rgba(13, 18, 31, 0.95); border: 1px solid var(--border-cyan); border-radius: 6px; padding: 14px;">
        <div style="font-size: 0.85rem; font-weight: bold; color: var(--border-cyan); margin-bottom: 8px;">
          🧭 OPERATOR INCIDENT REVIEW
        </div>
        <div style="font-size: 0.8rem; margin-bottom: 10px; color: ${statusColor};">
          Status: <strong>${reviewStatus}</strong>${reviewDecision ? ` | Decision: ${reviewDecision.toUpperCase()}` : ""}
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px;">
          <button class="btn-approve" onclick="window.reviewIncident('${incident.id}', 'approve')">✓ Approve</button>
          <button class="btn-danger" onclick="window.reviewIncident('${incident.id}', 'reject')">✕ Reject</button>
          <button class="btn-cyan" onclick="window.reviewIncident('${incident.id}', 'override')">↺ Override</button>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">
          AI recommendations remain advisory until a qualified operator authorizes action.
        </div>
      </div>
    `;
  }

  window.reviewIncident = async function (incidentId, decision) {
    const payload = {
      decision,
      reviewer: "Lead Safety Controller",
      notes: `Operator ${decision}d AI recommendation for incident ${incidentId}.`
    };

    try {
      const res = await fetch(`/api/incidents/${incidentId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        console.warn("Incident review failed", res.status);
        return;
      }

      const data = await res.json();
      const statusEl = document.getElementById("reviewSection");
      if (statusEl) {
        statusEl.innerHTML = `
          <div style="background: rgba(13, 18, 31, 0.95); border: 1px solid var(--border-cyan); border-radius: 6px; padding: 14px;">
            <div style="font-size: 0.85rem; font-weight: bold; color: var(--border-cyan); margin-bottom: 8px;">
              🧭 OPERATOR INCIDENT REVIEW
            </div>
            <div style="font-size: 0.8rem; color: var(--safe-green);">
              Review recorded: <strong>${data.review_decision.toUpperCase()}</strong> by ${data.reviewed_by}. Status: ${data.status}
            </div>
          </div>
        `;
      }
      if (activeIncidentId) selectIncident(activeIncidentId);
    } catch (err) {
      console.warn("Incident review request failed:", err);
    }
  };

  function renderAnnouncements(announcements) {
    // optional list update
  }

  // Handle Live WebSocket Events
  window.resqWS.on("status_change", (data) => {
    const dot = document.getElementById("wsIndicator");
    const label = document.getElementById("wsLabel");
    if (dot && label) {
      if (data.connected) {
        dot.className = "pulse-indicator";
        label.innerText = "LIVE WS ONLINE";
        label.style.color = "var(--safe-green)";
      } else {
        dot.className = "pulse-indicator danger";
        label.innerText = "WS RECONNECTING...";
        label.style.color = "var(--warning-amber)";
      }
    }
  });

  window.resqWS.on("new_incident", (data) => {
    console.log("WebSocket event: new_incident", data);
    loadInitialData();
  });

  window.resqWS.on("evacuation_routes_updated", () => {
    if (activeIncidentId) selectIncident(activeIncidentId);
  });

  window.resqWS.on("hazard_detected", () => {
    loadInitialData();
  });

  loadInitialData();
});
