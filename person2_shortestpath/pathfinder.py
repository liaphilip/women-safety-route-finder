# pathfinder.py
# Dijkstra + a simple Yen's K-shortest implementation (small graphs).
from typing import Dict, List, Tuple, Any
import heapq
import copy

def dijkstra(adj: Dict[str, List[Tuple[str, dict]]],
             start: str,
             end: str,
             weight_map: Dict[str, float]):
    """
    adj: node -> list of (neighbor, edge_dict). edge_dict must have 'id'
    weight_map: edge_id -> weight (float)
    Returns: (node_path, total_cost, edge_list) or (None, inf, [])
    """
    pq = [(0.0, start, [], [start])]  # (cost, node, edges_so_far, nodes_so_far)
    visited = {}

    while pq:
        cost, u, edges_so_far, nodes_so_far = heapq.heappop(pq)
        if u in visited: 
            continue
        visited[u] = cost
        if u == end:
            return nodes_so_far, cost, edges_so_far
        for v, e in adj.get(u, []):
            eid = e["id"]
            w = weight_map.get(eid, 1.0)
            if v in visited: 
                continue
            heapq.heappush(pq, (cost + w, v, edges_so_far + [e], nodes_so_far + [v]))
    return None, float("inf"), []

def yen_k_shortest(adj, start, end, weight_map, K=3):
    """
    Basic Yen's algorithm for K simple shortest paths.
    Returns list of (nodes, cost, edges)
    """
    A = []
    B = []

    first = dijkstra(adj, start, end, weight_map)
    if first[0] is None:
        return []
    A.append(first)

    for k in range(1, K):
        prev_nodes, prev_cost, prev_edges = A[k-1]
        for i in range(len(prev_nodes) - 1):
            spur_node = prev_nodes[i]
            root_nodes = prev_nodes[:i+1]

            # deep-copy adj
            adj_cp = {n: [(v, copy.deepcopy(e)) for (v, e) in nbrs] for n, nbrs in adj.items()}

            # remove edges that would create previously found paths with the same root
            for (a_nodes, a_cost, a_edges) in A:
                if a_nodes[:i+1] == root_nodes and len(a_nodes) > i+1:
                    u = a_nodes[i]; v = a_nodes[i+1]; eid_block = a_edges[i]["id"]
                    # remove u->v and v->u with that exact eid
                    adj_cp[u] = [(vv, ee) for (vv, ee) in adj_cp.get(u, []) if not (vv == v and ee["id"] == eid_block)]
                    adj_cp[v] = [(vv, ee) for (vv, ee) in adj_cp.get(v, []) if not (vv == u and ee["id"] == eid_block)]

            spur_path = dijkstra(adj_cp, spur_node, end, weight_map)
            if spur_path[0] is None:
                continue

            # combine root part and spur part (avoid duplicating spur_node)
            total_nodes = root_nodes[:-1] + spur_path[0]
            total_edges = prev_edges[:i] + spur_path[2]
            total_cost = sum(weight_map.get(e["id"], 1.0) for e in total_edges)
            candidate = (total_nodes, total_cost, total_edges)
            if candidate not in B:
                B.append(candidate)

        if not B:
            break
        B.sort(key=lambda x: x[1])
        A.append(B.pop(0))
    return A

def path_distance_weight_map(adj) -> Dict[str, float]:
    """
    Returns a map eid -> distance_m (for 'shortest by distance').
    """
    dist_map = {}
    for u, nbrs in adj.items():
        for v, e in nbrs:
            dist_map[e["id"]] = float(e.get("distance_m", 1.0))
    return dist_map

def summarize_edges(edges: List[dict]) -> dict:
    total_m = sum(float(e.get("distance_m", 0.0)) for e in edges)
    return {"distance_m": int(total_m), "edges": len(edges)}
