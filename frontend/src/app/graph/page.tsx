"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { MagnifyingGlass, ShareNetwork, CaretDown, CaretRight, X } from "@phosphor-icons/react";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

const NODE_TYPES = ["BankAccount", "Bank", "Utility", "Property", "Company", "Vehicle", "Travel", "City", "Person"];

const TYPE_COLORS: Record<string, string> = {
  Person: "#3b82f6", // Blue
  BankAccount: "#0284c7", // Sky Blue
  Bank: "#0d9488", // Teal
  Vehicle: "#f59e0b", // Amber
  Company: "#8b5cf6", // Purple
  Travel: "#ec4899", // Pink
  Property: "#f43f5e", // Rose
  Utility: "#10b981", // Emerald
  City: "#06b6d4", // Cyan
  Default: "#64748b" // Slate
};

export default function KnowledgeGraph() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get("id") || "";

  const [riskCategory, setRiskCategory] = useState("All");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  
  const [targetId, setTargetId] = useState(initialId);
  const [radius, setRadius] = useState(1);
  const [activeTypes, setActiveTypes] = useState<string[]>([
    "BankAccount", "Bank", "Utility", "Property", "Company", "Vehicle", "Travel", "City", "Person"
  ]);
  
  const [showControls, setShowControls] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);

  // Sync targetId with URL search params if present
  useEffect(() => {
    if (initialId) {
      setTargetId(initialId);
    }
  }, [initialId]);

  // Fetch citizens for dropdown
  const { data: citizensRes } = useSWR(
    `${API}/api/v1/citizens?page=1&page_size=50${riskCategory !== 'All' ? `&risk_level=${riskCategory}` : ''}${searchQuery ? `&search_query=${encodeURIComponent(searchQuery)}` : ''}`,
    fetcher
  );
  const citizens = citizensRes?.data || [];

  // Fetch graph data
  const { data: graphRes, error, isLoading } = useSWR(
    targetId ? `${API}/api/v1/graph/ego/${targetId}?radius=${radius}` : null,
    fetcher
  );

  useEffect(() => {
    if (!containerRef.current || !graphRes?.data) return;
    
    Promise.all([
      import("vis-network"),
      import("vis-data")
    ]).then(([visNet, visData]) => {
      const { Network } = visNet;
      const { DataSet } = visData;
      const graphData = graphRes.data;
      
      // Apply Node Type Filter (always include Center node)
      const filteredNodes = graphData.nodes.filter((n: any) => 
        n.id === targetId || activeTypes.includes(n.node_type)
      );
      const filteredNodeIds = new Set(filteredNodes.map((n: any) => n.id));
      const filteredEdges = graphData.edges.filter((e: any) => 
        filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
      );
      
      const nodes = new DataSet(
        filteredNodes.map((n: any) => {
          let cleanLabel = n.label || "";
          if (cleanLabel.endsWith(" ()")) cleanLabel = cleanLabel.replace(" ()", "");

          let t = `${cleanLabel}<br>Type: ${n.node_type}`;
          if (n.node_type === "Person") {
            if (n.cnic) t += `<br>CNIC: ${n.cnic}`;
            t += `<br>Risk Score: ${n.risk_score?.toFixed(1) || 0}`;
            if (n.declared_income) t += `<br>Income: PKR ${Number(n.declared_income).toLocaleString()}`;
          } else if (n.node_type === "BankAccount") {
            if (n.bank_name) t += `<br>Bank: ${n.bank_name}`;
            if (n.account_number || n.account_last4) t += `<br>Account: ${n.account_number || ('****' + n.account_last4)}`;
            if (n.account_type) t += `<br>Type: ${n.account_type}`;
            if (n.monthly_expenditure_pkr || n.monthly_expenditure) t += `<br>Monthly Spend: PKR ${Number(n.monthly_expenditure_pkr || n.monthly_expenditure).toLocaleString()}`;
            if (n.annual_expenditure_pkr || n.annual_expenditure) t += `<br>Annual Spend: PKR ${Number(n.annual_expenditure_pkr || n.annual_expenditure).toLocaleString()}`;
            if (n.city) t += `<br>City: ${n.city}`;
          } else if (n.node_type === "Bank") {
            t += `<br>Financial Institution: ${n.label || 'Bank'}`;
          } else if (n.node_type === "Vehicle") {
            if (n.car_brand) t += `<br>Brand: ${n.car_brand}`;
            if (n.car_model) t += `<br>Model: ${n.car_model}`;
            if (n.model_year) t += `<br>Year: ${n.model_year}`;
            if (n.engine_size_cc) t += `<br>Engine: ${n.engine_size_cc} CC`;
          } else if (n.node_type === "Travel") {
            if (n.destination) t += `<br>Destination: ${n.destination}`;
            if (n.passport_no) t += `<br>Passport: ${n.passport_no}`;
            if (n.visa_type) t += `<br>Visa Type: ${n.visa_type}`;
            if (n.reason_to_travel) t += `<br>Reason: ${n.reason_to_travel}`;
          } else if (n.node_type === "Company") {
            if (n.company_name) t += `<br>Company: ${n.company_name}`;
            if (n.entity_type) t += `<br>Entity Type: ${n.entity_type}`;
            if (n.status) t += `<br>Status: ${n.status}`;
            else if (n.company_status) t += `<br>Status: ${n.company_status}`;
            if (n.city) t += `<br>City: ${n.city}`;
            if (n.registered_office_address) t += `<br>Office: ${n.registered_office_address}`;
          } else if (n.node_type === "Property") {
            if (n.city) t += `<br>City: ${n.city}`;
            if (n.market_value) t += `<br>Value: PKR ${Number(n.market_value).toLocaleString()}`;
          } else if (n.node_type === "Utility") {
            if (n.consumer_id) t += `<br>Consumer ID: ${n.consumer_id}`;
            if (n.meter_no) t += `<br>Meter No: ${n.meter_no}`;
          }

          const tooltipEl = document.createElement("div");
          tooltipEl.innerHTML = t;
          tooltipEl.style.padding = "4px";
          tooltipEl.style.lineHeight = "1.5";

          const isPerson = n.node_type === "Person";
          const nodeColor = TYPE_COLORS[n.node_type] || TYPE_COLORS.Default;

          return {
            id: n.id,
            label: cleanLabel,
            shape: isPerson ? "dot" : "box",
            size: isPerson ? 20 : undefined,
            margin: isPerson ? undefined : { top: 8, bottom: 8, left: 12, right: 12 },
            color: {
              background: nodeColor,
              border: nodeColor,
              highlight: {
                background: nodeColor,
                border: "#0f172a"
              }
            },
            title: tooltipEl,
            font: { color: isPerson ? "#334155" : "#ffffff", size: 12, face: "Inter", bold: true },
            borderWidth: 2,
            shapeProperties: { borderRadius: 20 },
          };
        })
      );

      const edges = new DataSet(
        filteredEdges.map((e: any) => ({
          from: e.source,
          to: e.target,
          label: e.label,
          font: { size: 10, align: "middle", color: "#64748b" },
          color: { color: "#475569", highlight: "#10b981" },
          width: 1,
        }))
      );

      const options = {
        physics: {
          barnesHut: { gravitationalConstant: -3000, centralGravity: 0.3, springLength: 150 },
          stabilization: { iterations: 150 }
        },
        interaction: { hover: true, tooltipDelay: 200, zoomView: true },
        edges: { smooth: { type: "continuous" as const } }
      };

      if (networkRef.current) networkRef.current.destroy();
      networkRef.current = new Network(containerRef.current!, { nodes, edges } as any, options as any);
    });
  }, [graphRes, activeTypes, targetId]);

  return (
    <div className="flex flex-col gap-6 h-full min-h-[80vh]">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-slate-200">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
           Knowledge Graph Explorer
        </h1>
        <p className="text-sm text-slate-500">Interactive visualization of individual entity networks</p>
      </header>

      <div className="flex flex-col rounded-md overflow-hidden bg-white border border-slate-200 shadow-sm">
        <button 
          onClick={() => setShowControls(!showControls)}
          className="bg-[#0f172a] px-4 py-3 text-sm font-bold text-white flex items-center gap-2 hover:bg-slate-800 transition-colors cursor-pointer w-full text-left"
        >
          {showControls ? <CaretDown size={16} /> : <CaretRight size={16} />}
           Graph Controls
        </button>
        
        {showControls && (
          <div className="p-4 flex flex-col gap-6 text-slate-800 bg-white">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Select Risk Category</label>
                <select 
                  className="bg-white border border-slate-300 text-sm rounded px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 shadow-sm"
                  value={riskCategory}
                  onChange={(e) => {
                    setRiskCategory(e.target.value);
                    setTargetId("");
                  }}
                >
                  <option value="All">All</option>
                  <option value="A">A</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D</option>
                  <option value="E">E</option>
                </select>
              </div>
              <div className="flex flex-col gap-2 md:col-span-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <MagnifyingGlass size={14} className="text-blue-600" /> Search Citizen Name or CNIC (Press Enter):
                </label>
                <input 
                  type="text" 
                  className="bg-white border border-slate-300 text-sm rounded px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 w-full shadow-sm placeholder-slate-400"
                  placeholder="e.g. 35202..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setSearchQuery(searchInput);
                      setTargetId("");
                    }
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Select Citizen to Inspect</label>
                <select 
                  className="bg-white border border-blue-400 text-sm rounded px-3 py-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 shadow-sm"
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                >
                  <option value="">--- Select Citizen ---</option>
                  {citizens.map((c: any) => (
                    <option key={c.citizen_id} value={c.citizen_id}>
                      {c.canonical_name || "Unknown"} - {c.citizen_id}
                    </option>
                  ))}
                </select>
              </div>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Node Types to Show</label>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {NODE_TYPES.map(type => {
                      const isActive = activeTypes.includes(type);
                      return (
                        <button
                          key={type}
                          onClick={() => {
                            if (isActive) setActiveTypes(activeTypes.filter(t => t !== type));
                            else setActiveTypes([...activeTypes, type]);
                          }}
                          className={`px-2 py-1 rounded text-xs font-bold flex items-center gap-1 border transition-colors ${isActive ? 'bg-blue-100 text-blue-800 border-blue-200' : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'}`}
                        >
                          {type} {isActive && <X size={12} />}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">Graph Depth (Connections) <span className="text-slate-400 text-[10px] border border-slate-300 rounded-full w-3 h-3 flex items-center justify-center cursor-help" title="Max distance from center node">?</span></label>
                  <div className="flex items-center gap-4 pt-2">
                    <label className="flex items-center gap-2 text-sm text-slate-700 font-medium cursor-pointer">
                      <input type="radio" name="depth" value="1" checked={radius === 1} onChange={() => setRadius(1)} className="accent-blue-600 w-4 h-4" /> 1
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700 font-medium cursor-pointer">
                      <input type="radio" name="depth" value="2" checked={radius === 2} onChange={() => setRadius(2)} className="accent-blue-600 w-4 h-4" /> 2
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

      <div className="flex flex-col flex-1 relative border border-[#0f172a] rounded-lg shadow-sm">
        {targetId && (
          <div className="absolute top-4 right-4 bg-white/95 p-3 rounded-lg border border-slate-200 shadow-sm z-10 text-xs font-bold text-slate-700 flex flex-col gap-2 backdrop-blur-sm pointer-events-none">
            <div className="mb-1 text-slate-400 uppercase tracking-wider text-[10px]">Legend</div>
            {Object.entries(TYPE_COLORS).filter(([k]) => k !== 'Default').map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full border border-slate-200 shadow-inner" style={{ backgroundColor: color }}></div>
                {type}
              </div>
            ))}
          </div>
        )}
        <div ref={containerRef} className="w-full bg-slate-50" style={{ height: "650px" }}>
          {!targetId && (
            <div className="w-full h-full flex items-center justify-center text-slate-500 font-mono text-sm uppercase tracking-wider">
              Select a citizen to view their network
            </div>
          )}
          {isLoading && targetId && (
            <div className="w-full h-full flex items-center justify-center text-blue-600 font-mono text-sm uppercase font-bold tracking-widest">
              Building subgraph...
            </div>
          )}
          {error && (
            <div className="w-full h-full flex items-center justify-center text-red-600 font-mono text-sm font-bold bg-red-50">
              Target not found or API error
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
