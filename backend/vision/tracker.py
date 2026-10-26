import math
from typing import Dict, List, Tuple, Any


class CentroidTracker:
    """Lightweight and robust object tracker for maintaining persistent track IDs across frames.
    Prevents duplicate people counts caused by re-detecting the same person in subsequent frames.
    """

    def __init__(self, max_disappeared: int = 20, max_distance: float = 60.0):
        self.next_object_id = 1
        self.objects: Dict[int, Tuple[int, int]] = {}  # object_id -> (cx, cy)
        self.disappeared: Dict[int, int] = {}  # object_id -> frame_count
        self.bboxes: Dict[int, List[int]] = {}  # object_id -> [x1, y1, x2, y2]
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid: Tuple[int, int], bbox: List[int]) -> int:
        object_id = self.next_object_id
        self.objects[object_id] = centroid
        self.bboxes[object_id] = bbox
        self.disappeared[object_id] = 0
        self.next_object_id += 1
        return object_id

    def deregister(self, object_id: int) -> None:
        self.objects.pop(object_id, None)
        self.disappeared.pop(object_id, None)
        self.bboxes.pop(object_id, None)

    def update(self, rects: List[List[int]]) -> List[Dict[str, Any]]:
        """Update tracker with list of bounding boxes [x1, y1, x2, y2].
        Returns tracked objects list: [{'id': id, 'bbox': bbox, 'centroid': (cx, cy)}]
        """
        if len(rects) == 0:
            # Mark all existing objects as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return []

        # Calculate centroids for input rects
        input_centroids = []
        for rect in rects:
            cx = int((rect[0] + rect[2]) / 2.0)
            cy = int((rect[1] + rect[3]) / 2.0)
            input_centroids.append((cx, cy))

        # If currently tracking no objects, register all
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i], rects[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Compute distance matrix between existing objects and input centroids
            distances = []
            for i, oc in enumerate(object_centroids):
                row = []
                for j, ic in enumerate(input_centroids):
                    dist = math.hypot(oc[0] - ic[0], oc[1] - ic[1])
                    row.append(dist)
                distances.append(row)

            # Match greedily based on minimum distance
            used_rows = set()
            used_cols = set()

            # Flatten and sort distance pairs
            sorted_pairs = []
            for r in range(len(object_ids)):
                for c in range(len(input_centroids)):
                    sorted_pairs.append((distances[r][c], r, c))
            sorted_pairs.sort(key=lambda x: x[0])

            for dist, r, c in sorted_pairs:
                if r in used_rows or c in used_cols:
                    continue
                if dist > self.max_distance:
                    continue

                obj_id = object_ids[r]
                self.objects[obj_id] = input_centroids[c]
                self.bboxes[obj_id] = rects[c]
                self.disappeared[obj_id] = 0
                used_rows.add(r)
                used_cols.add(c)

            # Check unused rows (disappeared)
            for r, obj_id in enumerate(object_ids):
                if r not in used_rows:
                    self.disappeared[obj_id] += 1
                    if self.disappeared[obj_id] > self.max_disappeared:
                        self.deregister(obj_id)

            # Check unused cols (new objects)
            for c, ic in enumerate(input_centroids):
                if c not in used_cols:
                    self.register(ic, rects[c])

        # Return current active tracked objects
        results = []
        for obj_id, centroid in self.objects.items():
            if self.disappeared.get(obj_id, 0) == 0:
                results.append({
                    "id": obj_id,
                    "centroid": centroid,
                    "bbox": self.bboxes.get(obj_id, [centroid[0]-10, centroid[1]-10, centroid[0]+10, centroid[1]+10]),
                })
        return results
