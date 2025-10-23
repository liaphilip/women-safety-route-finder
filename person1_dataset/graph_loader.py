# graph_loader.py
# This file loads the nodes.json and edges.json files
# and builds the graph structure (adjacency list)
import json
from typing import Dict, List, Tuple

def load_nodes(path="data/nodes.json"):
    # just reads the nodes.json file into a dict
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    nodes = {}
    for n in raw:
        nid = n["id"]
        nodes[nid] = {"id": nid, "name": n.get("name", nid)}
    return nodes

def load_edges(path="data/edges.json"):
    # just reads the edges.json file into a list
    with open(path, "r", encoding="utf-8") as f:
        edges = json.load(f)


    counter = {}
    for e in edges:
        u = e.get("u"); v = e.get("v")
        key = f"{u}-{v}"
        counter[key] = counter.get(key, 0) + 1
        if "id" not in e:
            e["id"] = f"{u}-{v}-{counter[key]}"
        if "distance" in e and "distance_m" not in e:
            e["distance_m"] = e["distance"] # fix missing key
    return edges

def build_graph(nodes_path="data/nodes.json", edges_path="data/edges.json"):
    """
    Returns:
      nodes: (dict) all the nodes
      edges: (list) all the edges
      adj: (dict) the adjacency list
    """
    nodes = load_nodes(nodes_path)
    edges = load_edges(edges_path)

    # create the adjacency list
    adj = {nid: [] for nid in nodes}
    for e in edges:
        u = e["u"]; v = e["v"]
        if u not in adj: adj[u] = []
        if v not in adj: adj[v] = []
        
        # undirected graph, so add edge in both directions
        adj[u].append((v, e))
        adj[v].append((u, e))
        

        
    return nodes, edges, adj

# quick debug
if __name__ == "__main__":
    nodes, edges, adj = build_graph()
    print("Nodes:", list(nodes.keys()))
    print("Edges:", [e["id"] for e in edges][:10])
