const incidentList = document.getElementById('incident-list');
const agentPanel = document.getElementById('agent-panel');
const timeline = document.getElementById('timeline');
const incidentCount = document.getElementById('incident-count');
const clock = document.getElementById('clock');
const systemMode = document.getElementById('system-mode');

const incidentData = [
  { title: 'Fire on Floor 2', type: 'Fire', severity: 'High' },
  { title: 'Medical emergency', type: 'Medical', severity: 'Urgent' },
  { title: 'Earthquake impact', type: 'Earthquake', severity: 'Critical' },
];

const agentData = [
  { name: 'MASTER', state: 'processing' },
  { name: 'TRIAGE', state: 'completed' },
  { name: 'PEOPLE', state: 'processing' },
  { name: 'HAZARD', state: 'completed' },
  { name: 'RESOURCE', state: 'warning' },
  { name: 'ROUTE', state: 'tool call' },
  { name: 'SAFETY', state: 'completed' },
  { name: 'DECISION', state: 'processing' },
];

const timelineData = [
  ['08:12:41', 'Incident created', 'SYSTEM'],
  ['08:13:02', 'People analysis completed', 'PEOPLE'],
  ['08:13:18', 'Hazard agents reported smoke', 'HAZARD'],
  ['08:13:44', 'Resource recommendation queued', 'RESOURCE'],
  ['08:14:05', 'Alternate route calculated', 'ROUTE'],
];

function renderIncidents() {
  incidentList.innerHTML = incidentData.map((incident) => `
    <div class="item-card">
      <strong>${incident.title}</strong>
      <div>${incident.type}</div>
      <div class="status-pill ${incident.severity === 'Critical' ? 'red' : 'warning'}">${incident.severity}</div>
    </div>
  `).join('');
  incidentCount.textContent = incidentData.length;
}

function renderAgents() {
  agentPanel.innerHTML = agentData.map((agent) => `
    <div class="agent-card">
      <strong>${agent.name}</strong>
      <div class="status-pill">${agent.state.toUpperCase()}</div>
    </div>
  `).join('');
}

function renderTimeline() {
  timeline.innerHTML = timelineData.map(([time, event, tag]) => `
    <div class="timeline-item">
      <div class="time">${time}</div>
      <div class="event">${event}</div>
      <div class="tag">${tag}</div>
    </div>
  `).join('');
}

function updateClock() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString([], { hour12: false });
}

renderIncidents();
renderAgents();
renderTimeline();
updateClock();
setInterval(updateClock, 1000);

fetch('http://localhost:8000/api/dashboard')
  .then((response) => response.json())
  .then((data) => {
    if (data.mode) systemMode.textContent = data.mode.toUpperCase();
    if (data.active_incidents) incidentCount.textContent = data.active_incidents;
  })
  .catch(() => {
    systemMode.textContent = 'DEMO';
  });
