# graph_loader.py
# Loads nodes.json (list of {id,name}) and edges.json (list with modes & distance_m)
# Builds an undirected adjacency list: adj[node] -> list[(neighbor, edge_dict)]

import json
from typing import Dict, List, Tuple

def load_nodes(path="data/nodes.json") -> Dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    nodes = {}
    for n in raw:
        nid = n["id"]
        nodes[nid] = {"id": nid, "name": n.get("name", nid)}
    return nodes

def load_edges(path="data/edges.json") -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        edges = json.load(f)

    # Give every edge a stable id if not present: "u-v-i"
    counter_map = {}
    for i, e in enumerate(edges):
        u, v = e["u"], e["v"]
        key = f"{u}-{v}"
        counter_map[key] = counter_map.get(key, 0) + 1
        if "id" not in e:
            e["id"] = f"{u}-{v}-{counter_map[key]}"
        # Normalize field names
        if "distance" in e and "distance_m" not in e:
            e["distance_m"] = e["distance"]
    return edges

def build_graph(nodes_path="data/nodes.json", edges_path="data/edges.json"):
    """
    Returns:
      nodes: dict[node_id] -> {id, name}
      edges: list[edge_dict]
      adj: dict[node_id] -> list of (neighbor_id, edge_dict)
    """
    nodes = load_nodes(nodes_path)
    edges = load_edges(edges_path)

    # initialize adjacency
    adj: Dict[str, List[Tuple[str, dict]]] = {nid: [] for nid in nodes}

    for e in edges:
        u, v = e["u"], e["v"]
        if u not in adj:
            adj[u] = []
        if v not in adj:
            adj[v] = []
        # Undirected graph: add both directions
        adj[u].append((v, e))
        adj[v].append((u, e))

    return nodes, edges, adj
