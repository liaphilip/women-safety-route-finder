import networkx as nx
import json

#********************************
# 1. Create empty graph
#*************************
def create_graph():
    return nx.Graph()

#*****************
# 2. Add a node
#*****************
def add_node(G, node_id, name, lat, lon):
    G.add_node(node_id, name=name, lat=lat, lon=lon)

#*****************
# 3. Add an edge
#*****************
def add_edge(G, from_id, to_id, distance_m, lighting=5, CCTV=0, crime=5):
    G.add_edge(from_id, to_id, distance=distance_m, lighting=lighting, CCTV=CCTV, crime=crime)

#**********************
# 5. Export to JSON
#*********************
def export_to_json(G, node_file="nodes.json", edge_file="edges.json"):
    nodes = [dict(id=n, **data) for n, data in G.nodes(data=True)]
    edges = [dict(source_id=u, target_id=v, **data) for u, v, data in G.edges(data=True)]
    
    with open(node_file, "w") as f:
        json.dump(nodes, f, indent=2)
    with open(edge_file, "w") as f:
        json.dump(edges, f, indent=2)

#*********************
# 6. Neighbors function
#*********************
def neighbors(G, node_id):
    if node_id not in G:
        return []
    return list(G.neighbors(node_id))

#*********************
# 7. Temporary remove node
#*********************
removed_nodes = {}  

def temp_remove(G, node_id):
    if node_id in G:
        removed_nodes[node_id] = list(G.edges(node_id, data=True))
        G.remove_node(node_id)

#*********************
# 8. Restore removed node
#*********************
def restore_node(G, node_id):
    if node_id in removed_nodes:
        G.add_node(node_id) 
        for u, v, attr in removed_nodes[node_id]:
            
            if not G.has_edge(u, v):
                G.add_edge(u, v, **attr)
        del removed_nodes[node_id]

#*********************
# 9. Block and restore edges
#*********************
blocked_edges = {}

def block_edge(G, u, v):
    key = tuple(sorted([u, v]))  
    if G.has_edge(u, v):
        blocked_edges[key] = G[u][v]
        G.remove_edge(u, v)

def restore_edge(G, u, v):
    key = tuple(sorted([u, v]))
    if key in blocked_edges:
        G.add_edge(u, v, **blocked_edges[key])
        del blocked_edges[key]

#stimulatingg data of delhi 
G = create_graph()

# 25 nodes
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
add_node(G, 16, "Lajpat Nagar", 28.5678, 77.2510)
add_node(G, 17, "Hauz Khas Village", 28.5495, 77.2016)
add_node(G, 18, "Connaught Place Outer Circle", 28.6320, 77.2190)
add_node(G, 19, "Saket Mall", 28.5240, 77.2125)
add_node(G, 20, "Rajouri Garden", 28.6442, 77.1195)
add_node(G, 21, "Green Park", 28.5712, 77.2080)
add_node(G, 22, "Vasant Kunj", 28.5525, 77.1660)
add_node(G, 23, "Dwarka Sector 21", 28.5863, 77.0417)
add_node(G, 24, "Nehru Place", 28.5492, 77.2596)
add_node(G, 25, "Pitampura", 28.7073, 77.1323)



# ~~~~~    34 connections ~~~~~~~~~~~~~~~~~~~

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
add_edge(G, 15, 16, 4500, 6, 0, 4)
add_edge(G, 16, 17, 2000, 7, 1, 3)
add_edge(G, 17, 18, 3000, 8, 1, 2)
add_edge(G, 18, 19, 4000, 7, 1, 4)
add_edge(G, 19, 20, 3500, 6, 1, 3)
add_edge(G, 20, 21, 2500, 8, 1, 2)
add_edge(G, 21, 22, 3000, 7, 1, 3)
add_edge(G, 22, 23, 4500, 6, 0, 4)
add_edge(G, 23, 24, 5000, 7, 1, 3)
add_edge(G, 24, 25, 4000, 6, 1, 2)
add_edge(G, 25, 15, 4800, 7, 0, 4)
add_edge(G, 3, 16, 5500, 8, 1, 3)
add_edge(G, 5, 18, 5200, 6, 1, 4)
add_edge(G, 10, 22, 6000, 7, 1, 3)

export_to_json(G, "test_nodes.json", "test_edges.json")
