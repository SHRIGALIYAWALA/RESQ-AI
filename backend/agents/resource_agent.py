from typing import Any, Dict, List, Optional


class ResourceAgent:
    """Specialized agent responsible for calculating required emergency equipment and responder units."""

    name = "RESOURCE_AGENT"

    def recommend_resources(
        self,
        incident_type: str,
        severity: str,
        building_resources: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        inc_type = incident_type.lower()
        sev = severity.lower()

        required_services = []
        equipment_needed = []
        responder_units = 1

        if "fire" in inc_type or "smoke" in inc_type:
            required_services.extend(["Fire Department / Engine Company", "EMS Standby", "Building Safety Officer"])
            equipment_needed.extend([
                {"item": "Class ABC Dry Chemical Extinguishers", "quantity": 3},
                {"item": "Standpipe Fire Hose", "quantity": 1},
                {"item": "Evacuation Wheelchairs", "quantity": 2},
            ])
            responder_units = 3 if sev in {"critical", "high"} else 2

        elif "medical" in inc_type:
            required_services.extend(["Emergency Medical Services (ALS/BLS Ambulance)", "First Responder Squad"])
            equipment_needed.extend([
                {"item": "Automated External Defibrillator (AED)", "quantity": 1},
                {"item": "Trauma First Aid Kit", "quantity": 2},
                {"item": "Stretcher / Spine Board", "quantity": 1},
            ])
            responder_units = 2

        elif "hazmat" in inc_type or "chemical" in inc_type:
            required_services.extend(["HazMat Response Team", "Fire Department", "Environmental Health"])
            equipment_needed.extend([
                {"item": "Level B Protective Suits", "quantity": 4},
                {"item": "Spill Containment Kit", "quantity": 2},
                {"item": "Air Quality Gas Detector", "quantity": 2},
            ])
            responder_units = 4

        else:
            required_services.extend(["Security Patrol", "Building Maintenance"])
            equipment_needed.extend([
                {"item": "Flashlights & Megaphones", "quantity": 2},
                {"item": "First Aid Kit", "quantity": 1},
            ])

        # Match with currently available building inventory
        available_matches = []
        if building_resources:
            for item in building_resources:
                res_type = str(item.get("resource_type", "")).lower()
                if any(k in res_type for k in ["fire", "extinguisher", "aed", "medical", "first", "chair"]):
                    available_matches.append(item)

        return {
            "agent": self.name,
            "status": "completed",
            "required_services": required_services,
            "equipment_needed": equipment_needed,
            "recommended_responder_units": responder_units,
            "priority": "HIGH" if sev in {"critical", "high"} else "STANDARD",
            "staging_area": "Main Exterior Entrance / Assembly Area Alpha",
            "available_in_building": available_matches,
        }
