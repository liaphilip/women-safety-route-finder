# graph_loader.py
# Phase 2: Data Loading
# Loads data/nodes.json and data/edges.json and builds adjacency list graph G.
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

    # Ensure each edge has an 'id' and 'distance_m'
    counter = {}
    for e in edges:
        u = e.get("u"); v = e.get("v")
        key = f"{u}-{v}"
        counter[key] = counter.get(key, 0) + 1
        if "id" not in e:
            e["id"] = f"{u}-{v}-{counter[key]}"
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

    adj: Dict[str, List[Tuple[str, dict]]] = {nid: [] for nid in nodes}
    for e in edges:
        u = e["u"]; v = e["v"]
        if u not in adj: adj[u] = []
        if v not in adj: adj[v] = []
        # undirected
        adj[u].append((v, e))
        adj[v].append((u, e))
    return nodes, edges, adj

# quick debug
if __name__ == "__main__":
    nodes, edges, adj = build_graph()
    print("Nodes:", list(nodes.keys()))
    print("Edges:", [e["id"] for e in edges][:10])
