"""
Graph Query Helpers — Convenience functions for querying the knowledge graph.
"""
from __future__ import annotations

from typing import Any

import networkx as nx


def get_ego_graph(G: nx.DiGraph, node_id: str, radius: int = 1) -> nx.DiGraph:
    """Extract the ego-graph (neighbourhood) around a node.

    Parameters
    ----------
    G : The full knowledge graph.
    node_id : Centre node.
    radius : Number of hops (1 = direct neighbours, 2 = neighbours of neighbours).
    """
    if node_id not in G:
        return nx.DiGraph()
    return nx.ego_graph(G, node_id, radius=radius, undirected=True)


def get_person_assets(G: nx.DiGraph, person_id: str) -> dict[str, list[dict]]:
    """Get all assets owned by a person, grouped by type.

    Returns
    -------
    dict with keys ``vehicles``, ``properties``, ``utilities``, ``travel``,
    ``businesses``, ``phones``, ``bank_accounts``.
    """
    assets: dict[str, list[dict]] = {
        "vehicles": [],
        "properties": [],
        "utilities": [],
        "travel": [],
        "businesses": [],
        "phones": [],
        "bank_accounts": [],
    }

    if person_id not in G:
        return assets

    type_map = {
        "Vehicle": "vehicles",
        "Property": "properties",
        "Utility": "utilities",
        "Travel": "travel",
        "Company": "businesses",
        "Phone": "phones",
        "BankAccount": "bank_accounts",
    }

    for neighbour in G.successors(person_id):
        data = dict(G.nodes[neighbour])
        node_type = data.get("node_type", "")
        category = type_map.get(node_type)
        if category:
            edge_data = G.edges[person_id, neighbour]
            assets[category].append({
                "id": neighbour,
                **data,
                "edge": dict(edge_data),
            })

    return assets


def get_shared_connections(G: nx.DiGraph, person1: str, person2: str) -> list[dict]:
    """Find nodes that are shared between two persons (common assets, addresses, phones)."""
    if person1 not in G or person2 not in G:
        return []

    neighbours1 = set(G.successors(person1)) | set(G.predecessors(person1))
    neighbours2 = set(G.successors(person2)) | set(G.predecessors(person2))
    shared = neighbours1 & neighbours2

    return [
        {"id": n, **dict(G.nodes[n])}
        for n in shared
        if G.nodes[n].get("node_type") != "Person"
    ]


def get_community_members(G: nx.DiGraph, community: set[str]) -> list[dict]:
    """Get details of person nodes in a community."""
    members = []
    for node_id in community:
        data = G.nodes.get(node_id, {})
        if data.get("node_type") == "Person":
            members.append({"id": node_id, **data})
    return sorted(members, key=lambda x: x.get("risk_score", 0), reverse=True)


def search_graph(
    G: nx.DiGraph,
    query: str,
    field: str = "label",
) -> list[dict]:
    """Search nodes by a field value (case-insensitive substring match).

    Parameters
    ----------
    query : Search string.
    field : Node attribute to search ('label', 'cnic', 'node_type', etc.).
    """
    query_lower = query.lower().strip()
    results: list[dict] = []

    for node_id, data in G.nodes(data=True):
        val = str(data.get(field, "")).lower()
        if query_lower in val:
            results.append({"id": node_id, **data})

    return results[:100]  # Cap at 100 results


def get_node_details(G: nx.DiGraph, node_id: str) -> dict[str, Any]:
    """Get full details of a node including its edges."""
    if node_id not in G:
        return {}

    data = dict(G.nodes[node_id])
    edges_out = [
        {"target": t, "relationship": d.get("relationship", ""), **d}
        for _, t, d in G.out_edges(node_id, data=True)
    ]
    edges_in = [
        {"source": s, "relationship": d.get("relationship", ""), **d}
        for s, _, d in G.in_edges(node_id, data=True)
    ]

    return {
        "id": node_id,
        **data,
        "edges_out": edges_out,
        "edges_in": edges_in,
        "degree": G.degree(node_id),
    }
