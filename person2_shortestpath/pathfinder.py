import heapq
import copy
from typing import Dict,List,Tuple,Optional
def _build_edge_lookup(adj:Dict[str,List[Tuple[str,dict]]])->Dict[str, dict]:
    lookup={}
    for u,nbrs in adj.items():
        for v,e in nbrs:
            eid=e.get("id")
            if eid and eid not in lookup:
                lookup[eid]=e
    return lookup
def dijkstra(adj:Dict[str,List[Tuple[str,dict]]],
             start:str,
             end:str,
             weight_map:Dict[str,float])->Tuple[Optional[List[str]],float,List[dict]]:
    dist={n:float("inf")for n in adj.keys()}
    prev_node={}   
    prev_edge={}  
    dist[start]=0.0
    pq=[(0.0,start)]
    visited=set()
    while pq:
        d_u,u=heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u==end:
            break
        for v,e in adj.get(u,[]):
            eid=e["id"]
            w=weight_map.get(eid,float("inf"))
            alt=d_u+w
            if alt<dist.get(v,float("inf")):
                dist[v]=alt
                prev_node[v]=u
                prev_edge[v]=eid
                heapq.heappush(pq,(alt,v))
    if dist.get(end,float("inf"))==float("inf"):
        return None,float("inf"),[]
    # reconstructing node path and edge list
    node_path=[]
    edge_list=[]
    cur=end
    while True:
        node_path.append(cur)
        if cur==start:
            break
        eid=prev_edge.get(cur)
        if eid is None:
            # should not happen if teh path already exists
            break
        # find the edge object in adjacency (choose any matching id)
        # build later with edge lookup
        cur=prev_node[cur]
    node_path.reverse()
    # build edge_list using node pairs and prev_edge mapping
    # reconstruct edges by walking node_path and finding corresponding edge id
    edge_lookup = _build_edge_lookup(adj)
    for i in range(len(node_path)-1):
        u = node_path[i]; v = node_path[i+1]
        # prefer prev_edge[v] if exists
        eid = prev_edge.get(v)
        edge_obj = None
        if eid and eid in edge_lookup:
            edge_obj = edge_lookup[eid]
        else:
            # fallback: find any edge in adj[u] that goes to v
            for (nbr, e) in adj.get(u, []):
                if nbr == v:
                    edge_obj = e
                    break
        if edge_obj is None:
            # unexpected, but skip
            continue
        edge_list.append(edge_obj)

    total_cost = dist.get(end, float("inf"))
    return node_path, total_cost, edge_list


def yen_k_shortest(adj: Dict[str, List[Tuple[str, dict]]],
                   start: str,
                   end: str,
                   weight_map: Dict[str, float],
                   K: int = 3) -> List[Tuple[List[str], float, List[dict]]]:
    """
    Simplified Yen's algorithm that depends on the correct Dijkstra above.
    Returns up to K simple paths as (node_path, cost, edge_list).
    """
    A: List[Tuple[List[str], float, List[dict]]] = []
    B: List[Tuple[List[str], float, List[dict]]] = []

    first = dijkstra(adj, start, end, weight_map)
    if first[0] is None:
        return []
    A.append(first)

    for k in range(1, K):
        prev_path_nodes, prev_cost, prev_edges = A[k-1]

        for i in range(len(prev_path_nodes) - 1):
            spur_node = prev_path_nodes[i]
            root_path = prev_path_nodes[:i+1]

            # copy adj
            adj_cp = {n: [(v, copy.deepcopy(e)) for (v, e) in nbrs] for n, nbrs in adj.items()}

            # remove edges that would recreate previous paths with the same root
            for (p_nodes, p_cost, p_edges) in A:
                if len(p_nodes) > i and p_nodes[:i+1] == root_path:
                    # remove the edge between p_nodes[i] and p_nodes[i+1] with matching edge id
                    u = p_nodes[i]; v = p_nodes[i+1]; eid_block = p_edges[i]["id"]
                    adj_cp[u] = [(vv, ee) for (vv, ee) in adj_cp.get(u, []) if not (vv == v and ee["id"] == eid_block)]
                    adj_cp[v] = [(vv, ee) for (vv, ee) in adj_cp.get(v, []) if not (vv == u and ee["id"] == eid_block)]

            # remove nodes in root path except spur node (to prevent revisiting)
            # According to Yen, we temporarily remove root nodes (except spur node) by clearing their adjacency
            removed_nodes = set(root_path[:-1])
            for rn in removed_nodes:
                adj_cp[rn] = []

            # compute spur path from spur_node to end
            spur_path_nodes, spur_cost, spur_edges = dijkstra(adj_cp, spur_node, end, weight_map)
            if spur_path_nodes is None:
                continue

            # build total path
            total_nodes = root_path[:-1] + spur_path_nodes
            total_edges = []
            # edges from root portion: collect edges between consecutive root nodes from original prev_edges
            # For indices < i, take prev_edges[0:i]
            total_edges.extend(prev_edges[:i])
            # then add spur_edges
            total_edges.extend(spur_edges)

            total_cost = 0.0
            for e in total_edges:
                total_cost += weight_map.get(e["id"], 0.0)

            candidate = (total_nodes, total_cost, total_edges)
            if candidate not in B:
                B.append(candidate)

        if not B:
            break
        B.sort(key=lambda x: x[1])
        A.append(B.pop(0))

    return A


def distance_map(adj: Dict[str, List[Tuple[str, dict]]]) -> Dict[str, float]:
    dmap = {}
    for u, nbrs in adj.items():
        for v, e in nbrs:
            dmap[e["id"]] = float(e.get("distance_m", 1.0))
    return dmap

def summarize_route(edges: List[dict]) -> dict:
    total = sum(float(e.get("distance_m", 0.0)) for e in edges)
    return {"distance_m": int(total), "n_edges": len(edges)}
