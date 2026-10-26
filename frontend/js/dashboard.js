const incidentList = document.getElementById('incident-list');
const agentPanel = document.getElementById('agent-panel');
const timeline = document.getElementById('timeline');
const incidentCount = document.getElementById('incident-count');
const clock = document.getElementById('clock');
const systemMode = document.getElementById('system-mode');
const systemStatus = document.getElementById('system-status');
const incidentForm = document.getElementById('incident-form');
const incidentCreateForm = document.getElementById('incident-create-form');
const formStatus = document.getElementById('form-status');
const incidents = [];

const agentData = [
  ['MASTER', 'coordination'], ['TRIAGE', 'triage review'], ['PEOPLE', 'occupancy'],
  ['HAZARD', 'hazard review'], ['RESOURCE', 'resource check'], ['ROUTE', 'route check'],
  ['SAFETY', 'safety review'], ['DECISION', 'operator approval']
];

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }));
}

function renderIncidents() {
  incidentCount.textContent = incidents.length;
  incidentList.innerHTML = incidents.length ? incidents.map((incident) => `
    <button class="item-card incident-card" type="button" data-incident-id="${incident.id}">
  <strong>${escapeHtml(incident.title)}</strong>
  <div>${escapeHtml(incident.incident_type)} / ${escapeHtml(incident.status)}</div>
  <div class="status-pill ${incident.severity === 'critical' ? 'red' : 'warning'}">${escapeHtml(incident.severity)}</div>
    </button>
  `).join('') : '<div class="empty-state">No incidents reported.</div>';
}

function renderAgents() {
  agentPanel.innerHTML = agentData.map(([name, state]) => `
    <div class="agent-card"><strong>${name}</strong><div class="status-pill">${state.toUpperCase()}</div></div>
  `).join('');
}

function updateClock() {
  clock.textContent = new Date().toLocaleTimeString([], { hour12: false });
}

async function loadDashboard() {
  systemStatus.textContent = 'Loading live backend state...';
  try {
    const response = await fetch('/api/dashboard', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
    const data = await response.json();
    incidents.splice(0, incidents.length, ...(data.incidents || []));
    systemMode.textContent = String(data.mode || 'unknown').toUpperCase();
    document.getElementById('building-count').innerHTML = `${data.buildings?.length || 0} <span>tracked</span>`;
    document.getElementById('resource-metric').innerHTML = `${(data.resources || []).filter((item) => item.status === 'available').length} <span>available</span>`;
    document.getElementById('route-metric').innerHTML = `${(data.routes || []).filter((item) => item.status !== 'available').length} <span>risk</span>`;
    if (data.buildings?.length) {
      const buildingId = data.buildings[0].id;
      const buildingResponse = await fetch(`/api/buildings/${buildingId}`);
      const occupancyResponse = await fetch(`/api/buildings/${buildingId}/occupancy-heatmap`);
      const readingsResponse = await fetch(`/api/buildings/${buildingId}/sensor-readings`);
      const building = await buildingResponse.json();
      const floorPlan = document.getElementById('floor-plan');
      floorPlan.innerHTML = building.rooms?.length
        ? building.rooms.map((room) => `<div class="room">${escapeHtml(room.name)}</div>`).join('')
        : '<div class="empty-state">No rooms registered for this building.</div>';
      const occupancy = occupancyResponse.ok ? await occupancyResponse.json() : { observations: [] };
      const readings = readingsResponse.ok ? await readingsResponse.json() : { readings: [] };
      const people = occupancy.observations.reduce((total, item) => total + Number(item.people_count || 0), 0);
      const hazards = readings.readings.filter((item) => item.hazard_review_required || item.value?.hazard || item.value?.alert).length;
      document.getElementById('occupancy-metric').innerHTML = `${people || '--'} <span>people</span>`;
      document.getElementById('occupancy-bar').style.width = `${Math.min(100, people ? 50 : 0)}%`;
      document.getElementById('hazard-metric').innerHTML = `${hazards || '--'} <span>active</span>`;
    }
    systemStatus.textContent = `Backend connected / ${data.mode || 'unknown'} mode / human review required`;
    renderIncidents();
  } catch (error) {
    systemMode.textContent = 'OFFLINE';
    systemStatus.textContent = `Backend unavailable: ${error.message}`;
    renderIncidents();
  }
}

document.getElementById('refresh-dashboard').addEventListener('click', loadDashboard);
document.getElementById('new-incident').addEventListener('click', () => {
  incidentForm.classList.toggle('hidden');
  if (!incidentForm.classList.contains('hidden')) incidentForm.querySelector('input').focus();
});

incidentCreateForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(incidentCreateForm));
  const buildingId = values.building_id ? Number(values.building_id) : null;
  const floor = values.floor ? Number(values.floor) : null;
  formStatus.textContent = 'Submitting incident to backend...';
  try {
    const response = await fetch('/api/incidents', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: values.title, incident_type: values.incident_type, description: values.description, building_id: buildingId, severity: values.severity, location: { floor, room: values.room || null } })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    formStatus.textContent = `Incident #${data.id} created and queued for human review.`;
    incidentCreateForm.reset();
    await loadDashboard();
  } catch (error) {
    formStatus.textContent = `Unable to create incident: ${error.message}`;
  }
});

incidentList.addEventListener('click', async (event) => {
  const card = event.target.closest('[data-incident-id]');
  if (!card) return;
  const response = await fetch(`/api/incidents/${card.dataset.incidentId}`);
  if (!response.ok) return;
  const incident = await response.json();
  systemStatus.textContent = `Selected incident #${incident.id}: ${incident.title} / ${incident.status} / ${incident.severity}`;
});

renderAgents();
updateClock();
setInterval(updateClock, 1000);
loadDashboard();
setInterval(loadDashboard, 10000);
