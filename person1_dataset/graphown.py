import json

def load_nodes(file_path="test_nodes.json"):
    """Load nodes from JSON file"""
    with open(file_path, "r") as f:
        nodes = json.load(f)
    return nodes

def load_edges(file_path="test_edges.json"):
    """Load edges from JSON file"""
    with open(file_path, "r") as f:
        edges = json.load(f)
    return edges

def build_graph(nodes, edges):
    """
    Create adjacency list for an undirected graph:
    graph[node_u][node_v] = edge_attributes
    """
    graph = {node['id']: {} for node in nodes}
    for edge in edges:
        u = edge['u']
        v = edge['v']
        graph[u][v] = edge
        graph[v][u] = edge  
    return graph




def get_distance(edge):
    return edge.get("distance_m", 0)

def normalize_attribute(value, max_value=10):
    return min(value, max_value) / max_value



def get_edge(u, v, graph):
   
    if u in graph and v in graph[u]:
        return graph[u][v]
    else:
        return None


def load_graph():
   
    nodes = load_nodes()
    edges = load_edges()
    graph = build_graph(nodes, edges)
    return graph
