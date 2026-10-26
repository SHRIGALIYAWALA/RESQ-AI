from typing import Any, Dict, List, Optional


class PeopleCounter:
    """Calculates zone and room occupancy from tracked people objects.
    Uses track centroids to assign people to configured polygonal or rectangular room zones.
    """

    def __init__(self):
        pass

    def count_by_zone(
        self,
        tracked_objects: List[Dict[str, Any]],
        zone_definitions: Optional[Dict[str, Dict[str, Any]]] = None,
        default_zone: str = "Main Area",
    ) -> Dict[str, Any]:
        """Group tracked people by zone.
        tracked_objects: [{'id': 1, 'centroid': (cx, cy), 'bbox': [...]}, ...]
        zone_definitions: {'Room 201': {'bbox': [0, 0, 320, 240], 'capacity': 20}, ...}
        """
        zone_counts: Dict[str, int] = {}
        tracked_people = [obj for obj in tracked_objects]
        total_people = len(tracked_people)

        if not zone_definitions:
            zone_counts[default_zone] = total_people
            return {
                "total_count": total_people,
                "zones": {
                    default_zone: {
                        "count": total_people,
                        "capacity": 20,
                        "occupancy_rate": round(total_people / 20.0, 2),
                        "status": "OVERCROWDED" if total_people > 20 else "NORMAL",
                    }
                },
            }

        # Match each person centroid to a zone bounding box
        unassigned_count = 0
        for person in tracked_people:
            cx, cy = person["centroid"]
            assigned = False
            for zone_name, zone_meta in zone_definitions.items():
                x1, y1, x2, y2 = zone_meta.get("bbox", [0, 0, 9999, 9999])
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    zone_counts[zone_name] = zone_counts.get(zone_name, 0) + 1
                    assigned = True
                    break
            if not assigned:
                unassigned_count += 1

        if unassigned_count > 0:
            zone_counts[default_zone] = zone_counts.get(default_zone, 0) + unassigned_count

        zones_result = {}
        for zone_name, count in zone_counts.items():
            cap = zone_definitions.get(zone_name, {}).get("capacity", 25) if zone_definitions else 25
            occ_rate = round(count / float(max(1, cap)), 2)
            status = "CRITICAL_OVERCROWDING" if occ_rate > 1.2 else ("WARNING" if occ_rate >= 0.9 else "NORMAL")
            zones_result[zone_name] = {
                "count": count,
                "capacity": cap,
                "occupancy_rate": occ_rate,
                "status": status,
            }

        return {
            "total_count": total_people,
            "zones": zones_result,
        }
