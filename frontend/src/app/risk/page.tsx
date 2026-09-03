"use client";

import { useState } from "react";
import useSWR from "swr";
import { ShieldWarning, TrendUp, MagnifyingGlassPlus, MagnifyingGlassMinus } from "@phosphor-icons/react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, Tooltip as RechartsTooltip, ScatterChart, Scatter, ZAxis, Legend } from "recharts";
import dynamic from "next/dynamic";

const Plot = dynamic(() => {
  return Promise.all([
    import('react-plotly.js/factory'),
    // @ts-ignore
    import('plotly.js-dist-min')
  ]).then(([factory, Plotly]) => {
    return factory.default(Plotly.default || Plotly);
  });
}, { ssr: false });

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

export default function RiskAnalytics() {
  const { data: riskRes, isLoading: riskLoading } = useSWR(`${API}/api/v1/risk/distribution`, fetcher);
  const { data: featureRes } = useSWR(`${API}/api/v1/risk/feature-importance`, fetcher);
  const { data: gapRes } = useSWR(`${API}/api/v1/risk/income-wealth-gap`, fetcher);

  const categories = riskRes?.data?.categories || [];
  const features = (featureRes?.data?.features || []).filter((f: any) => f.importance > 0);
  const gapData = gapRes?.data || [];

  const plotColors: any = { A: '#10b981', B: '#3b82f6', C: '#f59e0b', D: '#ea580c', E: '#dc2626' };
  const scatterTraces = ['B', 'C', 'D', 'A', 'E'].map(cat => ({
    x: gapData.filter((d: any) => d.risk_category === cat).map((d: any) => d.ratio),
    y: gapData.filter((d: any) => d.risk_category === cat).map((d: any) => d.deviation),
    type: 'scatter',
    mode: 'markers',
    name: cat,
    marker: { color: plotColors[cat], size: 8, opacity: 0.7, line: { width: 0 } }
  }));

  const scatterLayout = {
    autosize: true,
    margin: { l: 50, r: 20, t: 30, b: 50 },
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    xaxis: { 
      title: { text: "Income / Net Worth Ratio", font: { color: '#64748b', size: 12 } },
      gridcolor: "#e2e8f0", 
      linecolor: "#cbd5e1", 
      tickfont: { color: "#64748b", size: 11 },
      zerolinecolor: "#cbd5e1"
    },
    yaxis: { 
      title: { text: "Deviation Score", font: { color: '#64748b', size: 12 } },
      gridcolor: "#e2e8f0", 
      linecolor: "#cbd5e1", 
      tickfont: { color: "#64748b", size: 11 },
      zerolinecolor: "#cbd5e1"
    },
    legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right", font: { color: "#475569", size: 11 } },
    hovermode: "closest",
    dragmode: "zoom",
  };

  const riskBarData = categories.map((c: any) => ({
    name: `Cat ${c.category}`,
    count: c.count,
    color: c.color,
    label: c.label,
  }));

  return (
    <div className="flex flex-col gap-6 h-full">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Risk Analytics</h1>
        <p className="text-sm text-slate-500">ML model feature distribution, population-level risk, and top suspicious citizens.</p>
      </header>

      {/* Summary Stats */}
      {riskRes && (
        <div className="grid grid-cols-3 gap-6">
          <div className="rounded-md shadow-sm p-5 flex flex-col items-center bg-blue-50 border border-blue-200 text-blue-800">
            <span className="text-4xl font-bold">{riskRes.data.total_citizens.toLocaleString()}</span>
            <span className="text-xs uppercase tracking-widest font-medium opacity-80 mt-1">Total Citizens</span>
          </div>
          <div className="rounded-md shadow-sm p-5 flex flex-col items-center bg-green-50 border border-green-200 text-green-800">
            <span className="text-4xl font-bold">{riskRes.data.filer_count.toLocaleString()}</span>
            <span className="text-xs uppercase tracking-widest font-medium opacity-80 mt-1">Tax Filers</span>
          </div>
          <div className="rounded-md shadow-sm p-5 flex flex-col items-center bg-red-50 border border-red-200 text-red-800">
            <span className="text-4xl font-bold">{riskRes.data.non_filer_count.toLocaleString()}</span>
            <span className="text-xs uppercase tracking-widest font-medium opacity-80 mt-1">Non-Filers</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Chart */}
        <div className="gov-panel flex flex-col p-0 h-[400px]">
          <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
            <ShieldWarning /> Risk Category Distribution
          </div>
          <div className="flex-1 p-6">
            {riskLoading ? (
              <div className="flex items-center justify-center h-full text-slate-400 font-mono text-xs">ANALYZING MODEL...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskBarData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                  <YAxis tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                  <RechartsTooltip formatter={(value: any, name: any, props: any) => [value.toLocaleString(), props.payload.label]} cursor={{fill: '#f1f5f9'}} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {riskBarData.map((entry: any, idx: number) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ML Feature Importance */}
        <div className="gov-panel flex flex-col p-0 h-[400px]">
          <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
            <TrendUp /> ML Feature Importance ({featureRes?.data?.model_name || 'ensemble'})
          </div>
          <div className="p-6 flex-1 flex flex-col gap-3 overflow-y-auto">
            {features.map((f: any) => (
              <div key={f.feature} className="flex flex-col gap-1 border-b border-slate-100 pb-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-700">{f.feature.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</span>
                  <span className="font-mono text-blue-700">{(f.importance * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5">
                  <div className="bg-blue-600 h-full" style={{ width: `${f.importance * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Income-to-Wealth Scatter Plot */}
      <div className="gov-panel flex flex-col p-0 h-[450px]">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex justify-between items-center">
          <span>Income-to-Wealth Gap Analysis</span>
          <span className="text-[10px] font-mono text-slate-500 lowercase">risk_category</span>
        </div>
        <div className="flex-1 p-0 overflow-hidden">
          <Plot
            data={scatterTraces as any}
            layout={scatterLayout as any}
            useResizeHandler={true}
            style={{ width: "100%", height: "100%" }}
            config={{ displayModeBar: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d'] }}
          />
        </div>
      </div>

    </div>
  );
}
