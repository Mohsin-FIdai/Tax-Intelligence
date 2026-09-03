"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { WarningCircle, MagnifyingGlass } from "@phosphor-icons/react";
import CommunityGraphModal from "./CommunityGraphModal";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

export default function HiddenNetworks() {
  const [selectedCommunityId, setSelectedCommunityId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 60;
  
  const { data: commRes, isLoading, error } = useSWR(`${API}/api/v1/graph/communities?limit=10000`, fetcher);
  const { data: statsRes } = useSWR(`${API}/api/v1/graph/stats`, fetcher);

  const communities = commRes?.data || [];
  const stats = statsRes?.data;
  
  const filteredCommunities = communities.filter((c: any) => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    const matchId = c.community_id.toString().includes(query);
    const matchMembers = c.top_members && c.top_members.some((m: string) => String(m).toLowerCase().includes(query));
    const matchMemberIds = c.top_member_ids && c.top_member_ids.some((m: string) => String(m).toLowerCase().includes(query));
    return matchId || matchMembers || matchMemberIds;
  });

  const totalPages = Math.ceil(filteredCommunities.length / itemsPerPage);
  const paginatedCommunities = filteredCommunities.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  // Reset page to 1 when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  return (
    <div className="flex flex-col gap-6 h-full">
      {selectedCommunityId && (
        <CommunityGraphModal 
          communityId={selectedCommunityId} 
          onClose={() => setSelectedCommunityId(null)} 
        />
      )}
      
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Hidden Network Detection</h1>
        <p className="text-sm text-slate-500">AI-driven detection of hidden financial networks, suspicious clusters, and syndicate patterns.</p>
      </header>

      {/* Graph Stats Summary */}
      {stats && (
        <div className="grid grid-cols-4 gap-0 border border-slate-300 shadow-sm overflow-hidden bg-white">
          <div className="p-4 border-r border-slate-200">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Total Nodes</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{(stats.total_nodes || 0).toLocaleString()}</div>
          </div>
          <div className="p-4 border-r border-slate-200">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Total Edges</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{(stats.total_edges || 0).toLocaleString()}</div>
          </div>
          <div className="p-4 border-r border-slate-200">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Communities</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{stats.total_communities || communities.length}</div>
          </div>
          <div className="p-4">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Suspicious Clusters</div>
            <div className="text-2xl font-bold text-red-600 mt-1">{stats.suspicious_communities || 0}</div>
          </div>
        </div>
      )}

      <div className="gov-panel p-0 flex flex-col flex-1">
        <div className="p-4 border-b border-slate-300 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-4">
            <div className="relative">
              <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input 
                type="text" 
                placeholder="Search community ID, citizen name, or ID..." 
                className="pl-9 pr-4 py-1.5 border border-slate-300 rounded-sm text-sm focus:outline-none focus:border-blue-700 w-80" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="text-xs font-medium text-slate-500 uppercase tracking-widest">
            Showing {filteredCommunities.length} of {stats?.total_communities || communities.length} Communities
          </div>
        </div>

        <div className="p-4 overflow-auto flex-1 bg-slate-50">
          {isLoading && <div className="p-8 text-slate-500 text-sm font-mono text-center uppercase">Scanning network graph...</div>}
          {error && <div className="p-8 text-red-600 text-sm font-mono text-center uppercase">Failed to load network data</div>}
          
          {communities.length === 0 && !isLoading && !error && (
            <div className="p-8 text-slate-400 text-sm font-mono text-center uppercase">
              No suspicious communities detected in the current graph.
              <br/><span className="text-xs mt-2 block text-slate-400">This may mean the graph data has not been fully processed yet.</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedCommunities.map((comm: any, idx: number) => (
              <div key={comm.community_id || idx} className="bg-white border border-slate-300 shadow-sm p-4 hover:border-red-400 transition-colors flex flex-col">
                <div className="flex justify-between items-start border-b border-slate-200 pb-3 mb-3">
                  <div className="flex items-center gap-2">
                    <WarningCircle size={20} className="text-red-600" />
                    <h3 className="font-bold text-slate-900 text-sm">COMMUNITY {comm.community_id || idx}</h3>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded-sm border ${(comm.avg_risk_score || 0) > 50 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                    {(comm.avg_risk_score || 0) > 50 ? 'CRITICAL' : 'FLAGGED'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <div className="text-slate-500 uppercase tracking-widest text-[9px] mb-1">Members</div>
                    <div className="font-mono font-bold text-slate-900">{comm.member_count || 0}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 uppercase tracking-widest text-[9px] mb-1">Avg Risk Score</div>
                    <div className="font-mono font-bold text-slate-900">{(comm.avg_risk_score || 0).toFixed(1)}</div>
                  </div>
                </div>
                {comm.top_members && comm.top_members.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex-1">
                    <div className="text-[9px] text-slate-500 uppercase tracking-widest mb-1">Key Members</div>
                    <div className="text-xs text-slate-600 font-mono">{comm.top_members.slice(0, 3).join(', ')}</div>
                  </div>
                )}
                <button 
                  onClick={() => setSelectedCommunityId(comm.community_id || idx)}
                  className="mt-4 w-full bg-slate-100 hover:bg-slate-200 text-blue-700 font-bold text-xs py-2 uppercase border border-slate-300 transition-colors block text-center"
                >
                  Investigate
                </button>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-6 border-t border-slate-200 pt-4 flex justify-between items-center">
              <div className="text-xs text-slate-500 font-medium">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredCommunities.length)} of {filteredCommunities.length} communities
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 bg-white border border-slate-300 text-slate-600 rounded-sm text-xs font-bold uppercase disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
                >
                  Previous
                </button>
                <div className="px-3 py-1 bg-slate-100 border border-slate-200 text-slate-700 rounded-sm text-xs font-bold">
                  {currentPage} / {totalPages}
                </div>
                <button 
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 bg-white border border-slate-300 text-slate-600 rounded-sm text-xs font-bold uppercase disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
