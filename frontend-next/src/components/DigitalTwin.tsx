"use client";

interface GraphNode { id: string; node_type?: string; floor_number?: number; status?: string; risk_score?: number; occupancy?: number; }
interface GraphEdge { source: string; target: string; status?: string; distance_m?: number; }

interface DigitalTwinProps {
  floor: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  dangerRooms?: string[];
}

export function DigitalTwin({ floor, nodes, edges, dangerRooms = [] }: DigitalTwinProps) {
  const floorNodes = nodes.filter((node) => Number(node.floor_number || 1) === floor);
  const visibleIds = new Set(floorNodes.map((node) => node.id));
  const floorEdges = edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const exitIds = new Set(nodes.filter((node) => node.node_type === "exit").map((node) => node.id));
  const adjacency = new Map<string, string[]>();

  for (const edge of edges) {
    if (edge.status?.toLowerCase() === "blocked") continue;
    adjacency.set(edge.source, [...(adjacency.get(edge.source) || []), edge.target]);
    adjacency.set(edge.target, [...(adjacency.get(edge.target) || []), edge.source]);
  }

  const findExitRoute = (start: string): string[] | null => {
    const queue = [start];
    const previous = new Map<string, string | null>([[start, null]]);
    let destination: string | null = null;

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (exitIds.has(current)) {
        destination = current;
        break;
      }
      for (const neighbor of adjacency.get(current) || []) {
        if (!previous.has(neighbor)) {
          previous.set(neighbor, current);
          queue.push(neighbor);
        }
      }
    }

    if (!destination) return null;
    const route: string[] = [];
    for (let current: string | null = destination; current; current = previous.get(current) ?? null) {
      route.unshift(current);
    }
    return route;
  };

  const roomRoutes = floorNodes
    .filter((node) => node.node_type === "room")
    .map((node) => ({ room: node.id, path: findExitRoute(node.id) }));
  const routeEdgeKeys = new Set<string>();
  for (const { path } of roomRoutes) {
    if (!path) continue;
    for (let index = 0; index < path.length - 1; index += 1) {
      routeEdgeKeys.add([path[index], path[index + 1]].sort().join("\0"));
    }
  }
  const edgeKey = (source: string, target: string) => [source, target].sort().join("\0");

  const nodeGroups = [
    { type: "room", y: 8 },
    { type: "corridor", y: 32 },
    { type: "staircase", y: 56 },
    { type: "exit", y: 78 },
  ];
  const positions = new Map<string, { x: number; y: number }>();
  const unplacedNodes = [...floorNodes];

  for (const group of nodeGroups) {
    const groupNodes = unplacedNodes.filter((node) => node.node_type === group.type);
    groupNodes.forEach((node) => unplacedNodes.splice(unplacedNodes.indexOf(node), 1));
    groupNodes.forEach((node, index) => {
      const center = 50 + (index - (groupNodes.length - 1) / 2) * Math.min(28, 76 / Math.max(groupNodes.length - 1, 1));
      positions.set(node.id, { x: center - 13.5, y: group.y });
    });
  }

  unplacedNodes.forEach((node, index) => {
    const center = 50 + (index % 3 - 1) * 28;
    positions.set(node.id, { x: center - 13.5, y: 8 + Math.floor(index / 3) * 24 });
  });

  const colorFor = (node: GraphNode) => {
    if (dangerRooms.includes(node.id) || dangerRooms.includes(String(node.id))) return "border-danger bg-danger/20 text-danger";
    if (node.node_type === "exit" || node.status === "SAFE") return "border-safe bg-safe/15 text-safe";
    if ((node.risk_score || 0) > 0.5 || node.status === "DANGER") return "border-warning bg-warning/15 text-warning";
    return "border-cyan-400/50 bg-cyan-400/10 text-cyan-100";
  };

  return (
    <div className="relative min-h-[520px] overflow-auto rounded-lg border border-cyan-500/20 bg-[#061016] p-4">
      <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "linear-gradient(rgba(0,243,255,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(0,243,255,.12) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
      <div className="relative min-w-[720px] min-h-[540px]">
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 700" preserveAspectRatio="none" aria-hidden="true">
          {floorEdges.map((edge, index) => {
            const from = positions.get(edge.source);
            const to = positions.get(edge.target);
            if (!from || !to) return null;

            const startX = (from.x + 13.5) * 10;
            const startY = (from.y + 10) * 7;
            const endX = (to.x + 13.5) * 10;
            const endY = (to.y + 10) * 7;
            const middleY = (startY + endY) / 2;
            const path = startY === endY
              ? `M ${startX} ${startY} H ${endX}`
              : `M ${startX} ${startY} V ${middleY} H ${endX} V ${endY}`;

            return <path
              key={`${edge.source}-${edge.target}-${index}`}
              d={path}
              fill="none"
              stroke={edge.status?.toLowerCase() === "blocked" ? "#ef4444" : routeEdgeKeys.has(edgeKey(edge.source, edge.target)) ? "#4ade80" : "#22d3ee"}
              strokeOpacity={edge.status?.toLowerCase() === "blocked" || routeEdgeKeys.has(edgeKey(edge.source, edge.target)) ? 0.9 : 0.4}
              strokeWidth={routeEdgeKeys.has(edgeKey(edge.source, edge.target)) ? "3" : "2"}
              vectorEffect="non-scaling-stroke"
            />;
          })}
        </svg>
        {floorNodes.map((node) => {
          const position = positions.get(node.id) || { x: 10, y: 10 };
          return <div key={node.id} className={`absolute w-[27%] min-h-20 border-2 p-3 text-xs shadow-[0_0_14px_rgba(0,243,255,.12)] ${colorFor(node)}`} style={{ left: `${position.x}%`, top: `${position.y}%` }}>
            <strong className="block truncate font-mono">{node.id}</strong>
            <span className="block uppercase opacity-75">{node.node_type || "structure"}</span>
            {node.occupancy != null && <span className="block">People: {node.occupancy}</span>}
            <span className="block">{node.status || "SAFE"}</span>
          </div>;
        })}
        {!floorNodes.length && <p className="p-6 text-sm text-muted">No mapped structure on Floor {floor}.</p>}
      </div>
      <div className="relative mt-4 rounded border border-white/10 bg-black/30 p-3">
        <h3 className="mb-2 font-mono text-xs font-bold tracking-wide text-safe">AVAILABLE ROOM-TO-EXIT ROUTES</h3>
        {roomRoutes.length ? (
          <ul className="space-y-2 text-xs">
            {roomRoutes.map(({ room, path }) => (
              <li key={room} className="grid gap-1 sm:grid-cols-[140px_1fr]">
                <strong className="text-cyan-200">{room}</strong>
                {path
                  ? <span className="text-safe">{path.join(" → ")}</span>
                  : <span className="text-danger">No unblocked route to a mapped exit.</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted">No rooms are mapped on this floor.</p>
        )}
      </div>
    </div>
  );
}
