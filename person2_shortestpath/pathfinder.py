# pathfinder.py
# Phase 5: Pathfinding algorithms (Dijkstra + Yen's K-shortest simple)
import heapq
import copy
from typing import Dict, List, Tuple

def dijkstra(adj: Dict[str, List[Tuple[str, dict]]], start: str, end: str, weight_map: Dict[str, float]):
    """
    Returns (node_path, total_cost, edge_list) or (None, inf, []) if unreachable.
    """
    pq = [(0.0, start, [], [start])]
    visited = set()
    while pq:
        cost, node, edges_so_far, nodes_so_far = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            return nodes_so_far, cost, edges_so_far
        for nbr, e in adj.get(node, []):
            if nbr in visited:
                continue
            w = weight_map.get(e["id"], 1.0)
            heapq.heappush(pq, (cost + w, nbr, edges_so_far + [e], nodes_so_far + [nbr]))
    return None, float("inf"), []

def yen_k_shortest(adj, start, end, weight_map, K=3):
    """
    Simplified Yen's algorithm for K simple shortest paths.
    Returns list of (nodes, cost, edges).
    """
    A = []
    B = []

    first = dijkstra(adj, start, end, weight_map)
    if first[0] is None:
        return []
    A.append(first)

    for k in range(1, K):
        for i in range(len(A[k-1][0]) - 1):
            spur_node = A[k-1][0][i]
            root_nodes = A[k-1][0][:i+1]

            # copy adjacency
            adj_cp = {n: [(v, copy.deepcopy(e)) for (v, e) in nbrs] for n, nbrs in adj.items()}

            # remove edges that would recreate earlier paths with same root
            for (p_nodes, p_cost, p_edges) in A:
                if p_nodes[:i+1] == root_nodes and len(p_nodes) > i+1:
                    u = p_nodes[i]; v = p_nodes[i+1]; eid = p_edges[i]["id"]
                    adj_cp[u] = [(vv, ee) for (vv, ee) in adj_cp.get(u, []) if not (vv == v and ee["id"] == eid)]
                    adj_cp[v] = [(vv, ee) for (vv, ee) in adj_cp.get(v, []) if not (vv == u and ee["id"] == eid)]

            spur_path = dijkstra(adj_cp, spur_node, end, weight_map)
            if spur_path[0] is None:
                continue

            total_nodes = root_nodes[:-1] + spur_path[0]
            total_edges = A[k-1][2][:i] + spur_path[2]
            total_cost = sum(weight_map.get(e["id"], 1.0) for e in total_edges)
            candidate = (total_nodes, total_cost, total_edges)
            if candidate not in B:
                B.append(candidate)

        if not B:
            break
        B.sort(key=lambda x: x[1])
        A.append(B.pop(0))
    return A

def distance_map(adj) -> Dict[str, float]:
    dmap = {}
    for u, nbrs in adj.items():
        for v, e in nbrs:
            dmap[e["id"]] = float(e.get("distance_m", 1.0))
    return dmap

def summarize_route(edges: List[dict]) -> dict:
    dist = sum(float(e.get("distance_m", 0.0)) for e in edges)
    return {"distance_m": int(dist), "n_edges": len(edges)}
