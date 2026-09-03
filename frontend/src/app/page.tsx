"use client";

import { useState } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { Users, WarningCircle, CurrencyDollar, FileText } from "@phosphor-icons/react";
import { 
  PieChart, Pie, Cell, Tooltip as RechartsTooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer
} from "recharts";

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

export default function Home() {
  const { data: citizenRes, error: citizenErr } = useSWR(`${API}/api/v1/citizens?page_size=7000`, fetcher);
  const { data: riskRes } = useSWR(`${API}/api/v1/risk/distribution`, fetcher);

  const citizens: any[] = citizenRes?.data || [];
  const riskData = riskRes?.data;
  const totalCitizens = citizenRes?.total_count || citizens.length;

  // KPI calculations
  let highRiskCount = 0;
  let totalHiddenIncome = 0;
  let totalRecoverableTax = 0;
  const provTax: Record<string, number> = {};
  const scatterData: any[] = [];

  const [riskFilter, setRiskFilter] = useState<string>("All");

  const topRiskCitizens = [...citizens]
    .filter((c) => typeof c.estimated_recoverable_tax === "number" && c.estimated_recoverable_tax >= 0)
    .filter((c) => riskFilter === "All" || c.risk_category === riskFilter)
    .sort((a, b) => (b.estimated_recoverable_tax || 0) - (a.estimated_recoverable_tax || 0));

  citizens.forEach((c: any) => {
    if (c.risk_category === "D" || c.risk_category === "E") highRiskCount++;
    if (typeof c.estimated_hidden_income === "number") totalHiddenIncome += c.estimated_hidden_income;
    if (typeof c.estimated_recoverable_tax === "number") totalRecoverableTax += c.estimated_recoverable_tax;
    
    if (c.province && typeof c.estimated_recoverable_tax === "number") {
      provTax[c.province] = (provTax[c.province] || 0) + c.estimated_recoverable_tax;
    }
    
    const income = typeof c.declared_income === "number" ? c.declared_income : 0;
    const netWorth = typeof c.estimated_net_worth === "number" ? c.estimated_net_worth : 0;
    if (income > 0 && netWorth > 0) {
      scatterData.push({ x: income, y: netWorth, category: c.risk_category, name: c.canonical_name || c.name });
    }
  });

  // Risk pie data from dedicated endpoint
  const riskPieData = (riskData?.categories || []).map((cat: any) => ({
    name: `Cat ${cat.category}: ${cat.label}`,
    value: cat.count,
    color: cat.color,
  }));

  // Filing bar data from dedicated endpoint
  const filingBarData = riskData ? [
    { name: "Filer", count: riskData.filer_count, color: "#10b981" },
    { name: "Non-Filer", count: riskData.non_filer_count, color: "#dc2626" },
  ] : [];

  const provBarData = Object.entries(provTax)
    .map(([k, v]) => ({ name: k, tax: v }))
    .sort((a, b) => b.tax - a.tax);

  const formatPKR = (val: number) => {
    if (!val || isNaN(val)) return "0 PKR";
    if (val >= 1e12) return `${(val / 1e12).toFixed(2)}T PKR`;
    if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B PKR`;
    if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M PKR`;
    return `${val.toLocaleString()} PKR`;
  };

  const maxX = scatterData.length > 0 ? Math.max(...scatterData.map(d => d.x)) * 1.08 : 4000000;
  const maxY = scatterData.length > 0 ? Math.max(...scatterData.map(d => d.y)) * 1.08 : 180000000;

  const RISK_COLORS: Record<string, string> = { A: "#10b981", B: "#3b82f6", C: "#f59e0b", D: "#ea580c", E: "#dc2626" };

  const RADIAN = Math.PI / 180;
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight="bold">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">
          National Tax Recovery Dashboard
        </h1>
        <p className="text-sm text-slate-500">
          Tax data overview at a glance: compliance intelligence and estimated recoverable revenue.
        </p>
      </header>

      {citizenErr && (
        <div className="p-3 bg-red-50 border-l-4 border-red-700 text-red-700 text-sm font-medium">
          SYSTEM ERROR: Unable to connect to intelligence backend at {API}. Is it running?
        </div>
      )}

      {(!citizenRes && !citizenErr) && (
        <div className="text-sm text-slate-500 font-mono uppercase tracking-widest">Querying backend database...</div>
      )}

      {citizenRes && (
        <>
          {/* KPI Row */}
          <section className="grid grid-cols-1 md:grid-cols-4 gap-0 border border-slate-300 shadow-sm overflow-hidden bg-white">
            <MetricCard title="Total Citizens" value={totalCitizens.toLocaleString()} icon={<Users size={20} />} color="border-blue-500" />
            <MetricCard title="High Risk (Cat D+E)" value={highRiskCount.toLocaleString()} icon={<WarningCircle size={20} className="text-red-600" />} color="border-red-500" />
            <MetricCard title="Potential Hidden Income" value={formatPKR(totalHiddenIncome)} icon={<CurrencyDollar size={20} className="text-amber-500" />} color="border-amber-500" />
            <MetricCard title="Est. Recoverable Tax" value={formatPKR(totalRecoverableTax)} icon={<FileText size={20} className="text-green-600" />} color="border-green-500" borderRight={false} />
          </section>

          {/* Row 1: Risk Pie + Filing Bar */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-2">
            <div className="gov-panel p-0 flex flex-col h-[380px]">
              <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">
                Risk Category Distribution
              </div>
              <div className="flex-1 p-2">
                {riskPieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={riskPieData} cx="50%" cy="50%" innerRadius={80} outerRadius={140} paddingAngle={2} dataKey="value" label={renderCustomizedLabel} labelLine={false}>
                        {riskPieData.map((entry: any, idx: number) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip formatter={(value: any) => [value.toLocaleString(), "Citizens"]} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : <div className="flex items-center justify-center h-full text-slate-400 text-sm">Loading...</div>}
              </div>
            </div>
            
            <div className="gov-panel p-0 flex flex-col h-[380px]">
              <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">
                Filing Status Breakdown
              </div>
              <div className="flex-1 p-6">
                {filingBarData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={filingBarData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="name" tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                      <YAxis tick={{fontSize: 12}} axisLine={false} tickLine={false} />
                      <RechartsTooltip cursor={{fill: '#f1f5f9'}} formatter={(v: any) => [v.toLocaleString(), "Count"]} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {filingBarData.map((entry, index) => (
                          <Cell key={index} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="flex items-center justify-center h-full text-slate-400 text-sm">Loading...</div>}
              </div>
            </div>
          </div>

          {/* Row 2: Province Tax + Top Risk Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="gov-panel p-0 flex flex-col h-[400px]">
              <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">
                Estimated Recoverable Tax by Province (PKR)
              </div>
              <div className="flex-1 p-6">
                {provBarData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={provBarData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="name" tick={{fontSize: 10}} axisLine={false} tickLine={false} interval={0} angle={-20} textAnchor="end" height={50} />
                      <YAxis tickFormatter={(v) => formatPKR(v)} tick={{fontSize: 9}} width={80} axisLine={false} tickLine={false} />
                      <RechartsTooltip formatter={(value: any) => [formatPKR(value), "Tax Gap"]} cursor={{fill: '#f1f5f9'}} />
                      <Bar dataKey="tax" radius={[4, 4, 0, 0]}>
                        {provBarData.map((_, idx) => (
                          <Cell key={idx} fill={['#1e3a5f', '#2d5a88', '#3d7ab2', '#4d9adc', '#6dbaff', '#8dcfff', '#aeddff'][idx % 7]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="flex items-center justify-center h-full text-slate-400 text-sm">Loading...</div>}
              </div>
            </div>

            <div className="gov-panel p-0 flex flex-col h-[400px]">
              <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900 flex justify-between items-center">
                <span>Highest Risk Citizens (By Tax Gap)</span>
                <div className="flex items-center gap-2">
                  <select 
                    className="text-xs font-semibold uppercase border border-slate-300 rounded-sm px-2 py-1 text-slate-700 focus:outline-none focus:border-blue-700"
                    value={riskFilter}
                    onChange={(e) => setRiskFilter(e.target.value)}
                  >
                    <option value="All">All Categories</option>
                    <option value="A">Cat A</option>
                    <option value="B">Cat B</option>
                    <option value="C">Cat C</option>
                    <option value="D">Cat D</option>
                    <option value="E">Cat E</option>
                  </select>
                  <span className="bg-red-700 text-white text-[10px] px-1.5 py-0.5 rounded-sm">CRITICAL</span>
                </div>
              </div>
              <div className="flex-1 overflow-auto bg-white">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 sticky top-0 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Name</th>
                      <th className="px-4 py-2 text-slate-500 font-semibold uppercase">CNIC</th>
                      <th className="px-4 py-2 text-slate-500 font-semibold uppercase">City</th>
                      <th className="px-4 py-2 text-slate-500 font-semibold uppercase text-right">Tax Gap</th>
                      <th className="px-4 py-2 text-slate-500 font-semibold uppercase text-center">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {topRiskCitizens.map((c: any) => (
                      <tr key={c.citizen_id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-medium text-slate-900">{c.canonical_name || c.name || 'N/A'}</td>
                        <td className="px-4 py-3 font-mono text-slate-500">{c.cnic ? String(c.cnic).replace(/\.0$/, '') : 'N/A'}</td>
                        <td className="px-4 py-3 text-slate-600">{c.city || 'N/A'}</td>
                        <td className="px-4 py-3 font-mono text-slate-700 text-right">{formatPKR(c.estimated_recoverable_tax || 0)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="px-2 py-0.5 rounded-sm font-bold text-[10px]" style={{ backgroundColor: `${RISK_COLORS[c.risk_category]}20`, color: RISK_COLORS[c.risk_category], border: `1px solid ${RISK_COLORS[c.risk_category]}40` }}>
                            {c.risk_category}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {topRiskCitizens.length === 0 && (
                      <tr><td colSpan={5} className="p-4 text-center text-slate-400 font-mono">No data available</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Row 3: Scatter Plot */}
          {scatterData.length > 0 && (
            <div className="gov-panel p-0 flex flex-col h-[500px]">
              <div className="bg-slate-100 border-b border-slate-300 px-4 py-2.5 text-sm font-semibold uppercase tracking-wider text-slate-900 flex items-center justify-between">
                <span>Declared Income vs. Estimated Net Worth</span>
                <span className="text-xs font-mono text-slate-500 normal-case font-normal">
                  {scatterData.length.toLocaleString()} active citizens plotted
                </span>
              </div>
              <div className="flex-1 p-3 bg-white">
                <Plot
                  data={Object.keys(RISK_COLORS).map((cat) => {
                    const catData = scatterData.filter(d => d.category === cat);
                    return {
                      x: catData.map(d => d.x),
                      y: catData.map(d => d.y),
                      type: 'scatter',
                      mode: 'markers',
                      name: `Cat ${cat}`,
                      marker: { color: RISK_COLORS[cat], size: 6.5, opacity: 0.75 },
                      text: catData.map(d => `<b>${d.name}</b><br>Declared Income: ${formatPKR(d.x)}<br>Estimated Net Worth: ${formatPKR(d.y)}<br>Risk Category: ${cat}`),
                      hoverinfo: 'text'
                    };
                  })}
                  layout={{
                    autosize: true,
                    margin: { t: 20, r: 24, b: 55, l: 85 },
                    xaxis: {
                      title: { text: 'Declared Annual Income (PKR)', font: { size: 12, color: '#334155' } },
                      range: [0, maxX],
                      tickfont: { size: 10, color: '#64748b' },
                      gridcolor: '#f1f5f9',
                      zerolinecolor: '#cbd5e1'
                    },
                    yaxis: {
                      title: { text: 'Estimated Net Worth (PKR)', font: { size: 12, color: '#334155' } },
                      range: [0, maxY],
                      tickfont: { size: 10, color: '#64748b' },
                      gridcolor: '#f1f5f9',
                      zerolinecolor: '#cbd5e1'
                    },
                    hovermode: 'closest',
                    plot_bgcolor: '#ffffff',
                    paper_bgcolor: 'transparent',
                    legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' }
                  }}
                  useResizeHandler={true}
                  style={{ width: "100%", height: "100%" }}
                  config={{ responsive: true, displaylogo: false, displayModeBar: true }}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MetricCard({ title, value, icon, color, borderRight = true }: { title: string; value: string; icon: React.ReactNode; color: string; borderRight?: boolean }) {
  return (
    <div className={`p-5 flex flex-col gap-2 border-t-4 ${color} ${borderRight ? 'border-r border-slate-200' : ''}`}>
      <div className="flex justify-between items-center text-slate-500">
        <span className="text-[11px] font-bold uppercase tracking-wider">{title}</span>
        {icon}
      </div>
      <div className="text-2xl font-semibold text-slate-900 tracking-tight">
        {value}
      </div>
    </div>
  );
}
