from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

report = []

root = client.get('/health')
report.append(f'HEALTH:{root.status_code}:{root.json()}')

building = client.post('/api/buildings', json={
    'name': 'RESQ Demo Building',
    'address': '123 Demo Street',
    'description': 'Demo building',
    'floors': [{'number': 1, 'name': 'Floor 1'}, {'number': 2, 'name': 'Floor 2'}],
    'rooms': [{'name': 'Lobby', 'floor_number': 1}, {'name': 'Lab 201', 'floor_number': 2}],
})
report.append(f'BUILDING:{building.status_code}:{building.json()}')

building_id = building.json()['id']

incident = client.post('/api/incidents', json={
    'title': 'Fire on floor 2',
    'incident_type': 'fire',
    'description': 'Smoke near Lab 201',
    'building_id': building_id,
    'location': {'floor': 2, 'room': 'Lab 201'}
})
report.append(f'INCIDENT:{incident.status_code}:{incident.json()}')

analysis = client.post('/api/incidents/analyze', json={
    'title': 'Medical emergency in auditorium',
    'incident_type': 'medical',
    'description': 'Person collapsed near auditorium entrance',
    'building_id': building_id,
    'location': {'floor': 1, 'room': 'Auditorium'}
})
report.append(f'ANALYZE:{analysis.status_code}:{analysis.json()}')

with open('verification_phase1.txt', 'w', encoding='utf-8') as handle:
    handle.write('\n'.join(report))

print('VERIFICATION_COMPLETE')
