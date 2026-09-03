"use client";

import { useState } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { MapPin } from "@phosphor-icons/react";

const MapComponent = dynamic(() => import("./MapComponent"), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center w-full h-full text-slate-400">Loading Map...</div>
});

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

const CITY_COORDS: Record<string, { lat: number, lon: number }> = {
  "Karachi": { lat: 24.8607, lon: 67.0011 },
  "Lahore": { lat: 31.5497, lon: 74.3436 },
  "Islamabad": { lat: 33.6844, lon: 73.0479 },
  "Rawalpindi": { lat: 33.5909, lon: 73.0537 },
  "Peshawar": { lat: 34.0151, lon: 71.5249 },
  "Quetta": { lat: 30.1798, lon: 66.9750 },
  "Multan": { lat: 30.1575, lon: 71.5249 },
  "Faisalabad": { lat: 31.4504, lon: 73.1350 },
  "Gujranwala": { lat: 32.1617, lon: 74.1883 },
  "Sialkot": { lat: 32.4945, lon: 74.5229 },
  "Hyderabad": { lat: 25.3960, lon: 68.3578 },
  "Sukkur": { lat: 27.7052, lon: 68.8574 },
  "Abbottabad": { lat: 34.1463, lon: 73.2117 },
  "Bahawalpur": { lat: 29.3956, lon: 71.6836 },
  "Bannu": { lat: 32.9861, lon: 70.6042 },
  "Chilas": { lat: 35.4129, lon: 74.0954 },
  "Gilgit": { lat: 35.9200, lon: 74.3137 },
  "Gwadar": { lat: 25.1216, lon: 62.3254 },
  "Hub": { lat: 25.0264, lon: 66.8845 },
  "Mirpur": { lat: 33.1425, lon: 73.7431 },
  "Muzaffarabad": { lat: 34.3597, lon: 73.4714 },
  "Rawalakot": { lat: 33.8582, lon: 73.7604 },
  "Skardu": { lat: 35.2982, lon: 75.6333 },
  "Turbat": { lat: 26.0031, lon: 63.0544 },
};

function formatPKR(val: number) {
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  return `${val.toLocaleString()}`;
}

export default function GeographicMap() {
  const { data: citizenRes } = useSWR(`${API}/api/v1/citizens?page_size=7000`, fetcher);
  const citizens = citizenRes?.data || [];

  // Aggregate by city
  const cityAgg: Record<string, { count: number, highRisk: number, totalScore: number, totalHidden: number }> = {};
  
  citizens.forEach((c: any) => {
    if (!c.city) return;
    const city = c.city.charAt(0).toUpperCase() + c.city.slice(1).toLowerCase();
    
    if (!cityAgg[city]) {
      cityAgg[city] = { count: 0, highRisk: 0, totalScore: 0, totalHidden: 0 };
    }
    
    cityAgg[city].count += 1;
    if (c.risk_category === "D" || c.risk_category === "E") {
      cityAgg[city].highRisk += 1;
    }
    cityAgg[city].totalScore += (c.deviation_score || 0);
    cityAgg[city].totalHidden += (c.estimated_hidden_income || 0);
  });

  const geoData = Object.keys(cityAgg).map(city => {
    const agg = cityAgg[city];
    const coords = CITY_COORDS[city] || { lat: 30.0, lon: 70.0 };
    return {
      city,
      lat: coords.lat,
      lon: coords.lon,
      totalCitizens: agg.count,
      highRiskCount: agg.highRisk,
      avgDeviation: agg.totalScore / agg.count,
      totalHidden: agg.totalHidden,
      hasCoords: !!CITY_COORDS[city]
    };
  }).filter(d => d.totalHidden > 0).sort((a, b) => b.totalHidden - a.totalHidden);

  const mapData = geoData.filter(d => d.hasCoords && d.highRiskCount > 0);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Geographic Risk Map</h1>
        <p className="text-sm text-slate-500">Spatial distribution of high-risk entities and flagged assets across Pakistan.</p>
      </header>

      <div className="gov-panel p-0 flex flex-col h-[500px]">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">Geospatial Intelligence Module</div>
        <div className="flex-1 w-full relative z-0">
          <MapComponent mapData={mapData} formatPKR={formatPKR} />
        </div>
      </div>

      <div className="gov-panel p-0 flex flex-col h-[400px]">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">
          Top High-Risk Regions
        </div>
        <div className="flex-1 overflow-auto bg-white">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 sticky top-0 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-slate-500 font-semibold uppercase">City</th>
                <th className="px-4 py-3 text-slate-500 font-semibold uppercase text-right">Total Citizens</th>
                <th className="px-4 py-3 text-slate-500 font-semibold uppercase text-right">High Risk Count</th>
                <th className="px-4 py-3 text-slate-500 font-semibold uppercase text-right">Avg Deviation Score</th>
                <th className="px-4 py-3 text-slate-500 font-semibold uppercase text-right">Total Hidden Income</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {geoData.map((d, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{d.city}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-600">{d.totalCitizens.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-600">{d.highRiskCount.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-600">{d.avgDeviation.toFixed(1)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-600">{formatPKR(d.totalHidden)}</td>
                </tr>
              ))}
              {geoData.length === 0 && (
                <tr><td colSpan={5} className="p-4 text-center text-slate-400 font-mono">No data available</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
