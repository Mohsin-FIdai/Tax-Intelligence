"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { MagnifyingGlass, Funnel, Eye, CircleNotch } from "@phosphor-icons/react";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

export default function CitizenRegistry() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [searchType, setSearchType] = useState("name");
  const [semantic, setSemantic] = useState(false);
  const [riskFilter, setRiskFilter] = useState("");
  const [provinceFilter, setProvinceFilter] = useState("");

  // Debounce search input by 350ms to prevent request queuing during typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);
  
  const isSearching = debouncedSearch.length > 0;
  
  // Build query string based on filters
  let url = isSearching 
    ? `${API}/api/v1/search?q=${encodeURIComponent(debouncedSearch)}&type=${searchType}&page=${page}&page_size=20${semantic ? '&semantic=true' : ''}`
    : `${API}/api/v1/citizens?page=${page}&page_size=20`;
    
  if (!isSearching) {
    if (riskFilter) url += `&risk_level=${riskFilter}`;
    if (provinceFilter) url += `&province=${encodeURIComponent(provinceFilter)}`;
  }
  
  const { data, error, isLoading } = useSWR(url, fetcher, { keepPreviousData: true });
  
  const citizens = isSearching ? (data?.data?.results || []) : (data?.data || []);
  const total = isSearching ? (data?.data?.total_count || 0) : (data?.total_count || 0);
  const totalPages = isSearching ? Math.ceil(total / 20) : (data?.total_pages || 1);

  return (
    <div className="flex flex-col gap-6 h-full">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">
          Citizen Registry
        </h1>
        <p className="text-sm text-slate-500">
          Master database of all registered entities with resolved identities and aggregated risk scores.
        </p>
      </header>

      <div className="gov-panel flex flex-col min-h-[600px]">
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-300 flex items-center justify-between bg-slate-50 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <select className="border border-slate-300 rounded-sm text-xs py-1.5 px-2 font-semibold text-slate-700 focus:outline-none focus:border-blue-700" value={searchType} onChange={(e) => setSearchType(e.target.value)}>
              <option value="name">By Name</option>
              <option value="cnic">By CNIC</option>
              <option value="phone">By Phone</option>
              <option value="business">By Business</option>
            </select>
            <div className="relative">
              {isLoading ? (
                <CircleNotch className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-600 animate-spin" size={16} />
              ) : (
                <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              )}
              <input 
                type="text" 
                placeholder="Search..." 
                className="pl-9 pr-4 py-1.5 border border-slate-300 rounded-sm text-sm focus:outline-none focus:border-blue-700 focus:ring-1 focus:ring-blue-700 w-64"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setDebouncedSearch(searchInput.trim());
                    setPage(1);
                  }
                }}
              />
            </div>
            
            <label className="flex items-center gap-2 cursor-pointer ml-2">
              <input 
                type="checkbox" 
                checked={semantic} 
                onChange={(e) => { setSemantic(e.target.checked); setPage(1); }}
                className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-600 focus:ring-2"
                disabled={searchType !== 'name'}
                title={searchType !== 'name' ? 'Semantic search is only available for name searches' : ''}
              />
              <span className={`text-xs font-bold uppercase ${searchType !== 'name' ? 'text-slate-400' : 'text-blue-700'}`}>Semantic AI Search</span>
            </label>
            
            <div className="h-6 w-px bg-slate-300 mx-1"></div>
            
            <div className="flex items-center gap-2">
              <Funnel className="text-slate-400" size={16} />
              <select 
                className="border border-slate-300 rounded-sm text-xs py-1.5 px-2 text-slate-700 focus:outline-none focus:border-blue-700" 
                value={riskFilter} 
                onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
                disabled={isSearching}
              >
                <option value="">All Risk Categories</option>
                <option value="A">Category A</option>
                <option value="B">Category B</option>
                <option value="C">Category C</option>
                <option value="D">Category D</option>
                <option value="E">Category E</option>
              </select>
              
              <select 
                className="border border-slate-300 rounded-sm text-xs py-1.5 px-2 text-slate-700 focus:outline-none focus:border-blue-700 w-36" 
                value={provinceFilter} 
                onChange={(e) => { setProvinceFilter(e.target.value); setPage(1); }}
                disabled={isSearching}
              >
                <option value="">All Provinces</option>
                <option value="Punjab">Punjab</option>
                <option value="Sindh">Sindh</option>
                <option value="Khyber Pakhtunkhwa">KPK</option>
                <option value="Balochistan">Balochistan</option>
                <option value="Islamabad Capital Territory">Islamabad</option>
                <option value="Gilgit-Baltistan">Gilgit-Baltistan</option>
                <option value="Azad Jammu and Kashmir">AJK</option>
              </select>
            </div>
          </div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-widest">
            {total.toLocaleString()} Records
          </div>
        </div>

        {/* Data Grid */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-slate-100 sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Citizen ID / CNIC</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Name</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Location</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Net Worth</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Deviation</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300">Risk</th>
                <th className="py-3 px-4 font-semibold text-slate-700 uppercase tracking-wider text-xs border-b border-slate-300 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading && (
                <tr><td colSpan={7} className="py-8 text-center text-slate-500 font-mono text-xs">LOADING DATA...</td></tr>
              )}
              {error && (
                <tr><td colSpan={7} className="py-8 text-center text-red-600 font-mono text-xs">CONNECTION TO BACKEND FAILED</td></tr>
              )}
              {!isLoading && !error && citizens.length === 0 && (
                <tr><td colSpan={7} className="py-8 text-center text-slate-400 font-mono text-xs">NO RECORDS FOUND</td></tr>
              )}
              {citizens.map((c: any) => {
                const cnic = c.cnic ? String(c.cnic).replace(/\.0$/, '') : "UNKNOWN";
                const displayName = c.canonical_name || c.name || "N/A";
                const devScore = typeof c.deviation_score === "number" ? c.deviation_score : 0;
                const netWorth = typeof c.estimated_net_worth === "number" ? c.estimated_net_worth : 0;
                return (
                  <tr key={c.citizen_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono text-xs text-slate-600">
                      <div className="font-semibold text-slate-900">{cnic}</div>
                      <span className="text-slate-400">{c.citizen_id}</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-900 flex items-center gap-2">
                        <span>{displayName}</span>
                        {c.urdu_name && !String(displayName).includes(c.urdu_name) && (
                          <span className="text-xs text-slate-500 font-sans tracking-normal" dir="rtl">
                            ({c.urdu_name})
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">{c.city || "N/A"}, {c.province || "N/A"}</td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-700">PKR {netWorth.toLocaleString()}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-[10px] font-bold uppercase rounded-sm border ${
                        devScore > 80 ? 'bg-red-50 text-red-700 border-red-200' : 
                        devScore > 50 ? 'bg-amber-50 text-amber-700 border-amber-200' : 
                        'bg-slate-100 text-slate-600 border-slate-200'
                      }`}>
                        {devScore.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center text-xs font-bold" style={{ color: c.risk_category === 'E' ? '#ff3355' : c.risk_category === 'D' ? '#ff8c00' : '#64748b' }}>
                      {c.risk_category || '-'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <a href={`/profile?id=${c.citizen_id}`} className="text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 p-1.5 rounded-sm border border-blue-200 transition-colors inline-flex" title="View Profile">
                        <Eye size={16} />
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-3 border-t border-slate-300 bg-slate-50 flex items-center justify-between">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-4 py-1.5 text-xs font-semibold uppercase border border-slate-300 text-slate-600 hover:bg-slate-100 disabled:opacity-40">
            Previous
          </button>
          <span className="text-xs font-mono text-slate-500">PAGE {page} OF {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-4 py-1.5 text-xs font-semibold uppercase border border-blue-700 text-blue-700 hover:bg-blue-50 disabled:opacity-40">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
