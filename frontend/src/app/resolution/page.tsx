"use client";

import { useState } from "react";
import useSWR, { mutate, preload } from "swr";
import { useEffect } from "react";
import { WarningCircle, CheckCircle, Question, ShieldCheck, ShieldWarning, CaretDown, CaretRight, CaretLeft, CircleNotch } from "@phosphor-icons/react";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

export default function EntityResolution() {
  const [page, setPage] = useState(1);
  const [filterSignal, setFilterSignal] = useState("All");
  const [filterDecision, setFilterDecision] = useState("All");
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [hiddenPairs, setHiddenPairs] = useState<string[]>([]);

  const [resolvedPage, setResolvedPage] = useState(1);
  const [silosFilter, setSilosFilter] = useState("All");
  const [confFilter, setConfFilter] = useState("All");

  const { data: summaryRes, mutate: mutateSummary } = useSWR(`${API}/api/v1/resolution/summary`, fetcher);
  const { data: reviewsRes, mutate: mutateReviews, isLoading: isReviewsLoading, isValidating: isReviewsValidating } = useSWR(`${API}/api/v1/resolution/reviews?page=${page}&limit=50&filter_signal=${encodeURIComponent(filterSignal)}&filter_decision=${encodeURIComponent(filterDecision)}`, fetcher, { keepPreviousData: true });
  const { data: resolvedRes, mutate: mutateResolved } = useSWR(`${API}/api/v1/resolution/resolved?page=${resolvedPage}&limit=50&silos_filter=${encodeURIComponent(silosFilter)}&conf_filter=${encodeURIComponent(confFilter)}`, fetcher, { keepPreviousData: true });

  const summary = summaryRes || { total_matches: 0, total_unique: 0, manual_reviews: 0, conflicts: 0 };
  const reviews = reviewsRes?.data || [];
  const visibleReviews = reviews.filter((r: any) => {
    const rec1 = r.record_a_id || r.record1_id;
    const rec2 = r.record_b_id || r.record2_id;
    return !hiddenPairs.includes(`${rec1}_${rec2}`);
  });
  const resolved = resolvedRes?.data || [];
  const totalPages = reviewsRes?.total_pages || 1;
  const totalReviewRecords = Math.max(0, (reviewsRes?.total_count || 0) - hiddenPairs.length);
  const resolvedTotalPages = resolvedRes?.total_pages || 1;
  const resolvedTotalCount = resolvedRes?.total_count || 0;

  const [showReviews, setShowReviews] = useState(true);
  const [showResolved, setShowResolved] = useState(true);

  // Preload next pages for instantaneous navigation
  useEffect(() => {
    if (page < totalPages) {
      preload(`${API}/api/v1/resolution/reviews?page=${page + 1}&limit=50&filter_signal=${encodeURIComponent(filterSignal)}&filter_decision=${encodeURIComponent(filterDecision)}`, fetcher);
    }
  }, [page, totalPages, filterSignal, filterDecision]);

  useEffect(() => {
    if (resolvedPage < resolvedTotalPages) {
      preload(`${API}/api/v1/resolution/resolved?page=${resolvedPage + 1}&limit=50&silos_filter=${encodeURIComponent(silosFilter)}&conf_filter=${encodeURIComponent(confFilter)}`, fetcher);
    }
  }, [resolvedPage, resolvedTotalPages, silosFilter, confFilter]);

  const handleDecision = async (r: any, decision: "MERGED" | "SEPARATED") => {
    const rec1 = r.record_a_id || r.record1_id;
    const rec2 = r.record_b_id || r.record2_id;
    const pairKey = `${rec1}_${rec2}`;
    
    // 1. Immediately dismiss from UI without waiting for reload
    setHiddenPairs((prev) => [...prev, pairKey]);
    setProcessingId(pairKey);
    
    try {
      const resp = await fetch(`${API}/api/v1/resolution/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ record1_id: rec1, record2_id: rec2, decision })
      });
      
      if (resp.ok) {
        // 2. Trigger fresh revalidation of all resolution endpoints
        await Promise.all([
          mutateSummary(),
          mutateReviews(),
          mutateResolved()
        ]);
      }
    } catch (e) {
      console.error("Decision update failed:", e);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Multi-Source, Multi-Lingual Entity Resolution</h1>
        <p className="text-sm text-slate-500">Identify fraud networks through phonetic matching, cross-script translation, and entity resolution using AI-driven scoring models.</p>
      </header>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Total Matches Resolved" value={summary.total_matches.toLocaleString()} color="border-emerald-500" valueColor="text-emerald-500" />
        <MetricCard title="Total Unique Citizens" value={summary.total_unique.toLocaleString()} color="border-blue-500" valueColor="text-blue-500" />
        <MetricCard title="Manual Reviews Required" value={summary.manual_reviews.toLocaleString()} color="border-amber-500" valueColor="text-amber-500" />
        <MetricCard title="Conflicts Detected" value={summary.conflicts.toLocaleString()} color="border-red-500" valueColor="text-red-500" />
      </div>

      {/* Review Required Section */}
      <div className="gov-panel p-0 flex flex-col">
        <button 
          onClick={() => setShowReviews(!showReviews)}
          className="bg-[#0f172a] px-4 py-3 text-sm font-bold uppercase tracking-wider text-white flex items-center justify-between hover:bg-slate-800 transition-colors cursor-pointer w-full text-left"
        >
          <div className="flex items-center gap-2">
            <ShieldWarning size={18} className="text-amber-600" /> Flagged & Conflicting Entities ({totalReviewRecords.toLocaleString()})
          </div>
          {showReviews ? <CaretDown size={16} /> : <CaretRight size={16} />}
        </button>
        
        {showReviews && (
          <>
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center flex-wrap gap-4">
              {/* Filter Tabs for Review Required vs Conflicts */}
              <div className="flex items-center gap-2 bg-slate-200/70 p-1 rounded-sm">
                <button
                  onClick={() => { setFilterDecision("All"); setPage(1); }}
                  className={`px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-wider transition-all ${
                    filterDecision === "All"
                      ? "bg-white text-slate-900 shadow-sm border border-slate-300"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  All Flagged ({ (summary.manual_reviews + summary.conflicts).toLocaleString() })
                </button>
                <button
                  onClick={() => { setFilterDecision("REVIEW"); setPage(1); }}
                  className={`px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 ${
                    filterDecision === "REVIEW"
                      ? "bg-amber-600 text-white shadow-sm"
                      : "text-amber-800 hover:bg-amber-100"
                  }`}
                >
                  <WarningCircle size={14} weight="bold" />
                  Review Required ({summary.manual_reviews.toLocaleString()})
                </button>
                <button
                  onClick={() => { setFilterDecision("CONFLICT"); setPage(1); }}
                  className={`px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5 ${
                    filterDecision === "CONFLICT"
                      ? "bg-red-600 text-white shadow-sm"
                      : "text-red-800 hover:bg-red-100"
                  }`}
                >
                  <ShieldWarning size={14} weight="bold" />
                  Conflicts ({summary.conflicts.toLocaleString()})
                </button>
              </div>

              {/* Signal Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-500 uppercase">Match Signal:</span>
                <select 
                  className="text-xs bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:border-blue-500"
                  value={filterSignal}
                  onChange={(e) => {
                    setFilterSignal(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="All">All Signals</option>
                  <option value="Matching CNIC">Matching CNIC</option>
                  <option value="CNIC and Name">CNIC and Name</option>
                  <option value="Name Only">Name Only</option>
                  <option value="Multilingual Name">Multilingual Name</option>
                </select>
              </div>
            </div>
            
            <div className="flex flex-col divide-y divide-slate-200 relative">
              {isReviewsValidating && visibleReviews.length > 0 && (
                <div className="absolute top-0 left-0 w-full h-1 bg-blue-100 overflow-hidden z-10">
                  <div className="h-full bg-blue-500 animate-[pulse_1s_ease-in-out_infinite] w-1/3 rounded"></div>
                </div>
              )}
              {isReviewsLoading && visibleReviews.length === 0 ? (
                <div className="p-12 text-center text-slate-500 font-mono text-xs flex items-center justify-center gap-2">
                  <CircleNotch size={18} className="animate-spin text-blue-600" />
                  LOADING CANDIDATES...
                </div>
              ) : visibleReviews.length === 0 ? (
                <div className="p-8 text-center text-slate-400 font-mono text-sm">
                  No records match the selected filter.
                </div>
              ) : (
                visibleReviews.map((r: any, i: number) => {
                  const rec1 = r.record_a_id || r.record1_id;
                  const rec2 = r.record_b_id || r.record2_id;
                  const pairKey = `${rec1}_${rec2}`;
                  const isProcessing = processingId === pairKey;

                  return (
                    <div key={i} className="p-4 hover:bg-slate-50 flex flex-col gap-3 transition-colors">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-bold text-slate-900 text-sm uppercase">
                            {r.source_domain_a || "Dataset A"} <span className="text-slate-400 mx-1">↔</span> {r.source_domain_b || "Dataset B"}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            {r.decision === "CONFLICT" ? (
                              <span className="text-xs font-bold px-2 py-0.5 bg-red-100 text-red-700 rounded-sm border border-red-200">CONFLICT DETECTED</span>
                            ) : (
                              <span className="text-xs font-bold px-2 py-0.5 bg-amber-100 text-amber-700 rounded-sm border border-amber-200">REVIEW REQUIRED</span>
                            )}
                            <span className="text-xs text-slate-600">{r.merge_reason}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Model Confidence</span>
                          <span className="font-mono text-lg font-bold text-slate-800">{r.confidence ?? 100}%</span>
                        </div>
                      </div>
                      
                      <div className="bg-slate-100 border border-slate-200 p-3 rounded-sm flex gap-8 flex-wrap lg:flex-nowrap">
                        <div className="flex-1 min-w-[300px]">
                          <div className="text-[10px] font-bold text-slate-500 uppercase mb-2 border-b border-slate-200 pb-1">AI Explainability</div>
                          <p className="text-xs text-slate-700 font-mono mb-3"><span className="text-slate-500">Matched Fields:</span> {r.reasons || "[]"}</p>
                          
                          <div className="mb-3 overflow-x-auto">
                            <table className="w-full text-left text-xs bg-white border border-slate-200">
                              <thead className="bg-slate-50 text-slate-500 uppercase border-b border-slate-200">
                                <tr>
                                  <th className="px-2 py-1 font-semibold">Field</th>
                                  <th className="px-2 py-1 font-semibold">Record A</th>
                                  <th className="px-2 py-1 font-semibold">Record B</th>
                                  <th className="px-2 py-1 font-semibold text-right">Status</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {['name', 'cnic', 'father_name', 'phone', 'address', 'city'].map(field => {
                                  const getFieldValue = (data: any, type: string) => {
                                    if (!data) return '';
                                    if (type === 'name') {
                                      return data['original_name'] || data['original_canonical_name'] || data['name'] || data['canonical_name'] || data['owner_name'] || data['Owner_Name'] || data['Person_Name'] || data['Traveler_Name'] || '';
                                    } else if (type === 'cnic') {
                                      return data['CNIC'] || data['cnic'] || data['original_cnic'] || '';
                                    } else if (type === 'father_name') {
                                      return data['original_father_name'] || data['father_name'] || data['Father_Name'] || '';
                                    } else if (type === 'phone') {
                                      return data['phone'] || data['Phone_Number'] || data['Contact_No'] || data['Owner_Number'] || '';
                                    } else if (type === 'address') {
                                      return data['address'] || data['Address'] || data['Registered_Office_Address'] || '';
                                    } else if (type === 'city') {
                                      return data['city'] || data['City'] || data['Home_City'] || '';
                                    }
                                    return '';
                                  };

                                  const va = String(getFieldValue(r.rec_a_data, field)).trim();
                                  const vb = String(getFieldValue(r.rec_b_data, field)).trim();
                                  const vA_display = va && va.toLowerCase() !== 'nan' ? va : 'Unknown';
                                  const vB_display = vb && vb.toLowerCase() !== 'nan' ? vb : 'Unknown';
                                  
                                  let status = "Differs";
                                  let statusColor = "text-amber-600";
                                  if (vA_display === "Unknown" || vB_display === "Unknown") {
                                    status = "Missing Data";
                                    statusColor = "text-slate-400";
                                  } else if (va.toLowerCase() === vb.toLowerCase()) {
                                    status = "Match";
                                    statusColor = "text-emerald-600";
                                  }
                                  
                                  return (
                                    <tr key={field} className="font-mono">
                                      <td className="px-2 py-1 font-bold text-slate-700">{field.replace('_', ' ').toUpperCase()}</td>
                                      <td className="px-2 py-1 truncate max-w-[150px]" title={vA_display}>{vA_display}</td>
                                      <td className="px-2 py-1 truncate max-w-[150px]" title={vB_display}>{vB_display}</td>
                                      <td className={`px-2 py-1 text-right font-bold ${statusColor}`}>{status}</td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>

                          <p className="text-[10px] text-slate-500 italic">Confidence is calculated via multi-layered probabilistic matching. Thresholds determine the final merge decision.</p>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex sm:flex-col gap-2 justify-center items-stretch min-w-[140px]">
                          <button 
                            onClick={() => handleDecision(r, "MERGED")}
                            disabled={isProcessing}
                            className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white px-4 py-2.5 text-xs font-bold uppercase rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
                          >
                            {isProcessing ? (
                              <CircleNotch size={14} className="animate-spin" />
                            ) : (
                              <CheckCircle size={14} weight="bold" />
                            )}
                            Force Merge
                          </button>
                          <button 
                            onClick={() => handleDecision(r, "SEPARATED")}
                            disabled={isProcessing}
                            className="bg-white border border-slate-300 hover:bg-slate-100 disabled:opacity-50 text-slate-700 px-4 py-2.5 text-xs font-bold uppercase rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
                          >
                            {isProcessing ? (
                              <CircleNotch size={14} className="animate-spin text-slate-600" />
                            ) : (
                              <WarningCircle size={14} weight="bold" />
                            )}
                            Keep Separate
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            
            <div className="p-3 border-t border-slate-200 bg-white flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">
                Page {page} of {totalPages.toLocaleString()}
              </span>
              <div className="flex gap-2">
                <button 
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-xs font-bold rounded-sm flex items-center gap-1 transition-colors"
                >
                  <CaretLeft size={14} /> Previous
                </button>
                <button 
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-xs font-bold rounded-sm flex items-center gap-1 transition-colors"
                >
                  Next <CaretRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Resolved Entities Table */}
      <div className="gov-panel p-0 flex flex-col">
        <button 
          onClick={() => setShowResolved(!showResolved)}
          className="bg-[#0f172a] px-4 py-3 text-sm font-bold uppercase tracking-wider text-white flex items-center justify-between hover:bg-slate-800 transition-colors cursor-pointer w-full text-left"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-emerald-600" /> Resolved Entities
          </div>
          {showResolved ? <CaretDown size={16} /> : <CaretRight size={16} />}
        </button>
        
        {showResolved && (
          <>
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center flex-wrap gap-4">
              <span className="text-xs text-slate-600 w-full md:w-auto">
                Browse all citizens that were merged from multiple source records. Each row shows the resolution basis and matched evidence.
              </span>
              <div className="flex items-center gap-4 w-full md:w-auto">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-500 uppercase">Cross-References (Silos)</span>
                  <select 
                    className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-medium focus:outline-none focus:border-blue-500"
                    value={silosFilter}
                    onChange={(e) => {
                      setSilosFilter(e.target.value);
                      setResolvedPage(1);
                    }}
                  >
                    <option value="All">All</option>
                    <option value="2+ Datasets">2+ Datasets</option>
                    <option value="3+ Datasets">3+ Datasets</option>
                    <option value="4+ Datasets">4+ Datasets</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-500 uppercase">Match Confidence</span>
                  <select 
                    className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-medium focus:outline-none focus:border-blue-500"
                    value={confFilter}
                    onChange={(e) => {
                      setConfFilter(e.target.value);
                      setResolvedPage(1);
                    }}
                  >
                    <option value="All">All</option>
                    <option value="High Confidence (>95%)">High Confidence (&gt;95%)</option>
                    <option value="Medium Confidence (80-95%)">Medium Confidence (80-95%)</option>
                    <option value="Low Confidence (<80%)">Low Confidence (&lt;80%)</option>
                  </select>
                </div>
              </div>
            </div>
        
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs whitespace-nowrap">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Citizen ID</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Name</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">CNIC</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Sources</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Source Datasets</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase">Resolution Basis</th>
                    <th className="px-4 py-2 text-slate-500 font-semibold uppercase text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {resolved.length === 0 ? (
                    <tr><td colSpan={7} className="p-4 text-center text-slate-400 font-mono">No resolved entities match this filter</td></tr>
                  ) : (
                    resolved.map((r: any, i: number) => {
                      const cnic = String(r.cnic || "");
                      const maskedCnic = cnic && cnic !== "nan" && cnic !== "Unknown" ? `***${cnic.slice(-4)}` : "N/A";
                      
                      return (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="px-4 py-2 font-mono text-slate-600">{r.citizen_id}</td>
                          <td className="px-4 py-2 font-bold text-slate-900">{r.canonical_name || "Unknown"}</td>
                          <td className="px-4 py-2 font-mono text-slate-500">{maskedCnic}</td>
                          <td className="px-4 py-2 font-bold text-slate-700 text-center">{r.dataset_count}</td>
                          <td className="px-4 py-2 text-slate-600 font-mono text-[10px]">{r.dataset_names}</td>
                          <td className="px-4 py-2 font-mono text-slate-500 text-[10px] truncate max-w-[250px]" title={r.matched_fields}>{r.matched_fields}</td>
                          <td className="px-4 py-2 font-bold text-emerald-600 text-right">{r.avg_confidence}%</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            <div className="p-3 border-t border-slate-200 bg-white flex justify-between items-center">
              <span className="text-xs text-slate-500 font-medium">
                Page {resolvedPage} of {resolvedTotalPages.toLocaleString()}
                <span className="mx-2 text-slate-300">|</span>
                Showing {(resolvedTotalCount || 0).toLocaleString()} resolved entities
              </span>
              <div className="flex gap-2">
                <button 
                  onClick={() => setResolvedPage(Math.max(1, resolvedPage - 1))}
                  disabled={resolvedPage === 1}
                  className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-xs font-bold rounded-sm flex items-center gap-1 transition-colors"
                >
                  <CaretLeft size={14} /> Previous
                </button>
                <button 
                  onClick={() => setResolvedPage(Math.min(resolvedTotalPages, resolvedPage + 1))}
                  disabled={resolvedPage === resolvedTotalPages}
                  className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-xs font-bold rounded-sm flex items-center gap-1 transition-colors"
                >
                  Next <CaretRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value, color, valueColor }: { title: string; value: string; color: string; valueColor: string }) {
  return (
    <div className={`gov-panel border-l-4 p-4 flex flex-col gap-1 ${color}`}>
      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{title}</span>
      <span className={`text-2xl font-bold font-mono ${valueColor}`}>{value}</span>
    </div>
  );
}
