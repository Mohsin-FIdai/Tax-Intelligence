import networkx as nx
import pandas as pd
from typing import List, Dict

class NetworkDetector:
    """
    Detects hidden wealth networks and shell companies using Graph Algorithms.
    """
    
    def __init__(self, graph: nx.Graph, citizens_df: pd.DataFrame):
        self.graph = graph
        self.citizens_df = citizens_df
        # Create a fast lookup for citizen info
        self.citizen_data = citizens_df.set_index("citizen_id").to_dict("index")

    def find_suspicious_networks(self) -> List[Dict]:
        """
        Find connected components in the knowledge graph.
        A component forms a 'network'. Calculate combined wealth vs income.
        """
        networks = []
        
        # Get all connected components (requires undirected graph)
        undirected_graph = self.graph.to_undirected() if self.graph.is_directed() else self.graph.copy()
        
        # Remove broad bridging nodes that connect entire cities into one component
        nodes_to_remove = [
            n for n, data in undirected_graph.nodes(data=True) 
            if data.get("node_type") in ["City", "Address", "Province"]
        ]
        undirected_graph.remove_nodes_from(nodes_to_remove)
        
        components = list(nx.connected_components(undirected_graph))
        
        for comp in components:
            members = []
            combined_wealth = 0.0
            combined_income = 0.0
            companies = []
            
            # Extract citizens and assets in this component
            for node in comp:
                node_data = self.graph.nodes[node]
                node_type = node_data.get("node_type")
                
                if node_type == "Person":
                    cid = str(node)
                    if cid in self.citizen_data:
                        c_info = self.citizen_data[cid]
                        members.append(str(c_info.get("canonical_name", cid)))
                        combined_wealth += float(c_info.get("estimated_net_worth", 0.0))
                        combined_income += float(c_info.get("declared_income", 0.0))
                
                elif node_type == "Company":
                    companies.append(str(node))
            
            # Only care about networks with more than 1 citizen and high wealth mismatch
            if len(members) > 1 and combined_wealth > 0:
                hidden_wealth = max(0, combined_wealth - combined_income)
                
                # Flag if hidden wealth is suspiciously large (> 5x combined income)
                if combined_income == 0 or (combined_wealth / combined_income > 5):
                    networks.append({
                        "nodes": list(comp),
                        "members": members,
                        "companies_involved": len(companies),
                        "combined_wealth": combined_wealth,
                        "combined_income": combined_income,
                        "hidden_wealth": hidden_wealth,
                        "suspicion_ratio": (combined_wealth / combined_income) if combined_income > 0 else float('inf')
                    })
                    
        # Sort by hidden wealth
        networks.sort(key=lambda x: x["hidden_wealth"], reverse=True)
        return networks

    def detect_shell_companies(self) -> List[Dict]:
        """
        Detect potential shell companies.
        A shell company is often a central node connecting multiple seemingly 
        unrelated individuals to high-value assets without intrinsic operations.
        For simplicity, we find businesses with multiple directors but low/no 
        associated revenue, or circular ownership.
        """
        shell_companies = []
        
        for node in self.graph.nodes:
            if self.graph.nodes[node].get("node_type") == "Company":
                # Find neighbors
                neighbors = list(self.graph.neighbors(node))
                citizens = [n for n in neighbors if self.graph.nodes[n].get("node_type") == "Person"]
                
                if len(citizens) >= 2:
                    # Business connecting multiple citizens
                    shell_companies.append({
                        "company": str(node),
                        "directors": len(citizens),
                        "risk_factor": "Multiple disconnected beneficial owners"
                    })
                    
        return shell_companies
