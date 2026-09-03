"""
Graph Analytics — Centrality, community detection, and suspicious subgraph extraction.
"""
from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np


def compute_centrality_metrics(G: nx.DiGraph) -> dict[str, dict[str, float]]:
    """Compute multiple centrality metrics for all nodes.

    Returns
    -------
    dict with keys ``degree``, ``betweenness``, ``pagerank``, each mapping
    node-id → score.
    """
    undirected = G.to_undirected()

    degree = nx.degree_centrality(undirected)
    betweenness = nx.betweenness_centrality(undirected, k=min(500, len(undirected)))
    pagerank = nx.pagerank(G, alpha=0.85, max_iter=100)

    return {
        "degree": degree,
        "betweenness": betweenness,
        "pagerank": pagerank,
    }


def detect_communities(G: nx.DiGraph) -> list[set[str]]:
    """Detect communities using the Louvain algorithm.

    Returns a list of sets, each containing node IDs belonging to a community.
    """
    undirected = G.to_undirected()
    try:
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(undirected, resolution=1.0, seed=42)
    except Exception:
        from networkx.algorithms.community import greedy_modularity_communities
        communities = list(greedy_modularity_communities(undirected))

    # Sort by size descending
    return sorted(communities, key=len, reverse=True)


def find_hidden_connections(G: nx.DiGraph, source: str, target: str, max_paths: int = 5) -> list[list[str]]:
    """Find shortest paths between two nodes, revealing hidden connections."""
    undirected = G.to_undirected()
    paths: list[list[str]] = []
    try:
        for path in nx.all_shortest_paths(undirected, source, target):
            paths.append(path)
            if len(paths) >= max_paths:
                break
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass
    return paths


def get_suspicious_subgraphs(
    G: nx.DiGraph,
    min_risk: float = 60.0,
    min_size: int = 3,
) -> list[nx.DiGraph]:
    """Extract subgraphs centred on high-risk person nodes.

    Parameters
    ----------
    min_risk : Minimum risk score for a person to anchor a subgraph.
    min_size : Minimum number of nodes in a returned subgraph.
    """
    suspicious_persons = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") == "Person" and d.get("risk_score", 0) >= min_risk
    ]
    subgraphs: list[nx.DiGraph] = []
    for person in suspicious_persons:
        ego = nx.ego_graph(G, person, radius=2, undirected=True)
        if ego.number_of_nodes() >= min_size:
            subgraphs.append(ego)

    # Deduplicate overlapping subgraphs
    seen_nodes: set[str] = set()
    unique: list[nx.DiGraph] = []
    for sg in sorted(subgraphs, key=lambda g: g.number_of_nodes(), reverse=True):
        sg_nodes = set(sg.nodes())
        if len(sg_nodes - seen_nodes) > 0:
            unique.append(sg)
            seen_nodes |= sg_nodes

    return unique


def get_graph_statistics(G: nx.DiGraph) -> dict[str, Any]:
    """Compute summary statistics for the knowledge graph."""
    undirected = G.to_undirected()
    node_types: dict[str, int] = {}
    edge_types: dict[str, int] = {}

    for _, data in G.nodes(data=True):
        nt = data.get("node_type", "Unknown")
        node_types[nt] = node_types.get(nt, 0) + 1

    for _, _, data in G.edges(data=True):
        et = data.get("relationship", "Unknown")
        edge_types[et] = edge_types.get(et, 0) + 1

    degrees = [d for _, d in undirected.degree()]

    return {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "density": round(nx.density(undirected), 6),
        "avg_degree": round(np.mean(degrees), 2) if degrees else 0,
        "max_degree": max(degrees) if degrees else 0,
        "connected_components": nx.number_connected_components(undirected),
        "node_types": node_types,
        "edge_types": edge_types,
    }


def get_person_nodes(G: nx.DiGraph) -> list[dict]:
    """Return a list of all Person nodes with their attributes."""
    persons = []
    for node_id, data in G.nodes(data=True):
        if data.get("node_type") == "Person":
            persons.append({"id": node_id, **data})
    return persons
