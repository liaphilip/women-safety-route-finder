import networkx as nx
import json

# -----------------
# 1. Create empty graph
# -----------------
def create_graph():
    return nx.Graph()

# -----------------
# 2. Add a node
# -----------------
def add_node(G, node_id, name, lat, lng, node_type="intersection"):
    G.add_node(node_id, name=name, lat=lat, lng=lng, type=node_type)

# -----------------
# 3. Add an edge
# -----------------
def add_edge(G, source, target, distance_m, lighting=5, CCTV=0, crowd=5, crime=5, nearest_police_m=500):
    G.add_edge(
        source, target,
        distance_m=distance_m,
        lighting=lighting,
        CCTV=CCTV,
        crowd=crowd,
        crime=crime,
        nearest_police_m=nearest_police_m
    )

# -----------------
# 5. Export to JSON
# -----------------
def export_to_json(G, node_file="nodes.json", edge_file="edges.json"):
    nodes = [dict(id=n, **data) for n, data in G.nodes(data=True)]
    edges = [dict(source_id=u, target_id=v, **data) for u, v, data in G.edges(data=True)]

    with open(node_file, "w") as f:
        json.dump(nodes, f, indent=2)
    with open(edge_file, "w") as f:
        json.dump(edges, f, indent=2)

G = create_graph()

# Add some nodes
import networkx as nx

def add_node(G, node_id, name, lat, lon):
    G.add_node(node_id, name=name, lat=lat, lon=lon)

def add_edge(G, from_id, to_id, distance_m, lighting, CCTV, crime):
    G.add_edge(from_id, to_id, distance=distance_m, lighting=lighting, CCTV=CCTV, crime=crime)

# Create graph
G = nx.Graph()

# --- Add nodes (15 Delhi locations) ---
add_node(G, 1, "Connaught Place", 28.6315, 77.2167)
add_node(G, 2, "Rajiv Chowk Metro", 28.6328, 77.2197)
add_node(G, 3, "India Gate", 28.6129, 77.2295)
add_node(G, 4, "Chandni Chowk", 28.6562, 77.2301)
add_node(G, 5, "Red Fort", 28.6562, 77.2410)
add_node(G, 6, "Karol Bagh", 28.6510, 77.1907)
add_node(G, 7, "IIT Delhi", 28.5450, 77.1926)
add_node(G, 8, "AIIMS Delhi", 28.5672, 77.2100)
add_node(G, 9, "Lotus Temple", 28.5535, 77.2588)
add_node(G, 10, "Akshardham Temple", 28.6127, 77.2773)
add_node(G, 11, "JNU Campus", 28.5402, 77.1666)
add_node(G, 12, "Indira Gandhi International Airport", 28.5562, 77.1000)
add_node(G, 13, "Qutub Minar", 28.5245, 77.1855)
add_node(G, 14, "Sarojini Nagar Market", 28.5754, 77.1996)
add_node(G, 15, "Delhi University North Campus", 28.6886, 77.2100)

# --- Add edges (20 connections with attributes) ---
add_edge(G, 1, 2, 500,   9, 1, 2)
add_edge(G, 1, 3, 2700,  8, 1, 3)
add_edge(G, 1, 6, 3500,  7, 1, 4)
add_edge(G, 2, 4, 3000,  6, 0, 5)
add_edge(G, 4, 5, 1200,  5, 0, 6)
add_edge(G, 3, 5, 5000,  7, 1, 4)
add_edge(G, 6, 4, 4000,  6, 0, 5)
add_edge(G, 6, 7, 8000,  8, 1, 3)
add_edge(G, 7, 8, 2500,  9, 1, 2)
add_edge(G, 8, 3, 4500,  8, 1, 3)
add_edge(G, 8, 9, 7000,  7, 1, 4)
add_edge(G, 9, 10, 9000, 6, 0, 5)
add_edge(G, 10, 3, 6500, 7, 1, 4)
add_edge(G, 4, 10, 7000, 6, 0, 6)
add_edge(G, 5, 10, 6000, 7, 1, 4)
add_edge(G, 7, 11, 5000, 8, 1, 3)
add_edge(G, 11, 12, 8000, 7, 1, 4)
add_edge(G, 12, 13, 7000, 6, 1, 5)
add_edge(G, 13, 14, 4000, 7, 1, 3)
add_edge(G, 14, 3, 4500, 8, 1, 3)
add_edge(G, 15, 4, 5000, 6, 0, 5)
# Print summary

# Export
export_to_json(G, "test_nodes.json", "test_edges.json")
