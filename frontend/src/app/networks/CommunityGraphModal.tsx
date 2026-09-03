"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useSWR from "swr";
import { X, ShieldWarning, ShieldCheck } from "@phosphor-icons/react";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => res.json());

const TYPE_COLORS: Record<string, string> = {
  Person: "#3b82f6", // Blue
  Vehicle: "#f59e0b", // Amber
  Company: "#8b5cf6", // Purple
  Travel: "#ec4899", // Pink
  Property: "#f43f5e", // Rose
  Utility: "#10b981", // Emerald
  BankAccount: "#0284c7", // Sky Blue
  Bank: "#0d9488", // Teal
  City: "#06b6d4", // Cyan
  Default: "#64748b" // Slate
};

export default function CommunityGraphModal({ communityId, onClose }: { communityId: number, onClose: () => void }) {
  const { data: graphRes, isLoading } = useSWR(`${API}/api/v1/graph/communities/${communityId}`, fetcher);
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || !graphRes?.data) return;

    Promise.all([
      import("vis-network"),
      import("vis-data")
    ]).then(([visNet, visData]) => {
      const { Network } = visNet;
      const { DataSet } = visData;

      const nodesData = graphRes.data.nodes || [];
      const edgesData = graphRes.data.edges || [];

      const nodes = new DataSet(
        nodesData.map((n: any) => {
          let tooltipHtml = `
            <div style="font-family: 'Inter', sans-serif; min-width: 200px;">
              <div style="font-weight: bold; font-size: 14px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin-bottom: 8px;">
                ${n.label} <span style="color: #64748b; font-size: 11px; font-weight: normal; margin-left: 4px;">(${n.node_type})</span>
              </div>
              <div style="font-size: 12px; display: grid; gap: 4px;">
          `;

          if (n.node_type === "Person") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>CNIC:</span> <strong>${n.cnic || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Risk Score:</span> <strong>${n.risk_score || "0"} (${n.risk_category || "A"})</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Income:</span> <strong>${n.declared_income ? "PKR " + Number(n.declared_income).toLocaleString() : "N/A"}</strong></div>
            `;
          } else if (n.node_type === "BankAccount") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Bank:</span> <strong>${n.bank_name || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Account:</span> <strong>${n.account_number || ("••••" + (n.account_last4 || "")) || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Type:</span> <strong>${n.account_type || "Current"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Monthly Spend:</span> <strong>${n.monthly_expenditure_pkr || n.monthly_expenditure ? "PKR " + Number(n.monthly_expenditure_pkr || n.monthly_expenditure).toLocaleString() : "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Annual Spend:</span> <strong>${n.annual_expenditure_pkr || n.annual_expenditure ? "PKR " + Number(n.annual_expenditure_pkr || n.annual_expenditure).toLocaleString() : "N/A"}</strong></div>
            `;
          } else if (n.node_type === "Bank") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Financial Institution:</span> <strong>${n.label || "Bank"}</strong></div>
            `;
          } else if (n.node_type === "Vehicle") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Brand:</span> <strong>${n.car_brand || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Model:</span> <strong>${n.car_model || "N/A"} (${n.model_year || "N/A"})</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Engine:</span> <strong>${n.engine_size_cc ? n.engine_size_cc + " CC" : "N/A"}</strong></div>
            `;
          } else if (n.node_type === "Travel") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Destination:</span> <strong>${n.destination || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Visa:</span> <strong>${n.visa_type || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Reason:</span> <strong>${n.reason_to_travel || "N/A"}</strong></div>
            `;
          } else if (n.node_type === "Property") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>City:</span> <strong>${n.city || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Value:</span> <strong>${n.market_value ? "PKR " + Number(n.market_value).toLocaleString() : "N/A"}</strong></div>
            `;
          } else if (n.node_type === "Utility") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Type:</span> <strong>${n.utility_type || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Consumer ID:</span> <strong>${n.consumer_id || "N/A"}</strong></div>
            `;
          } else if (n.node_type === "Company") {
            tooltipHtml += `
              <div style="display: flex; justify-content: space-between;"><span>Entity Type:</span> <strong>${n.entity_type || "N/A"}</strong></div>
              <div style="display: flex; justify-content: space-between;"><span>Status:</span> <strong>${n.status || n.company_status || "N/A"}</strong></div>
            `;
          }
          tooltipHtml += `</div></div>`;

          const tooltipEl = document.createElement("div");
          tooltipEl.innerHTML = tooltipHtml;

          const isPerson = n.node_type === "Person";
          const nodeColor = TYPE_COLORS[n.node_type] || TYPE_COLORS.Default;

          return {
            id: n.id,
            label: n.label,
            shape: isPerson ? "dot" : "box",
            size: isPerson ? n.size : undefined,
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
        edgesData.map((e: any) => ({
          from: e.source,
          to: e.target,
          label: e.label || e.relationship,
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
  }, [graphRes]);

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return createPortal(
    <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center z-[9999] p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl h-[85vh] flex flex-col border border-slate-300 overflow-hidden">
        
        {/* Header */}
        <div className="bg-[#0f172a] p-4 flex justify-between items-center text-white shrink-0">
          <div className="flex flex-col">
            <h2 className="font-bold tracking-tight text-lg uppercase flex items-center gap-2">
              <ShieldWarning size={20} className="text-amber-500" /> Community #{communityId} Investigation
            </h2>
            <p className="text-xs text-slate-300">
              Interactive subgraph showing community members and their connected entities.
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-md transition-colors text-slate-300 hover:text-white"
          >
            <X size={20} weight="bold" />
          </button>
        </div>

        {/* Legend */}
        <div className="bg-slate-100 border-b border-slate-200 p-2 flex gap-4 justify-center text-xs font-bold text-slate-600 shrink-0 flex-wrap">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            type !== "Default" && (
              <div key={type} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }}></div>
                <span className="uppercase">{type}</span>
              </div>
            )
          ))}
        </div>

        {/* Graph Canvas */}
        <div className="relative flex-1 bg-white min-h-0">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10 backdrop-blur-sm">
              <div className="text-slate-500 font-mono text-sm uppercase font-bold tracking-widest animate-pulse flex flex-col items-center gap-4">
                <ShieldCheck size={48} className="text-blue-500" />
                Loading Community Subgraph...
              </div>
            </div>
          )}
          <div ref={containerRef} className="w-full h-full" />
        </div>

      </div>
    </div>,
    document.body
  );
}
