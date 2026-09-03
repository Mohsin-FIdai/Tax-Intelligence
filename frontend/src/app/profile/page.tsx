"use client";

import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Suspense, useState } from "react";
import { User, IdentificationCard, ShieldWarning, Car, Buildings, House, AirplaneTilt, Lightning, Bank, ShareNetwork, Brain, CircleNotch, CaretDown, CaretUp } from "@phosphor-icons/react";
import GenerateNoticeButton from "@/components/GenerateNoticeButton";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then((res) => { if (!res.ok) throw new Error(res.statusText); return res.json(); });

function ProfileContent() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");

  const { data: profileRes, error: profileErr, isLoading } = useSWR(
    id ? `${API}/api/v1/citizens/${id}` : null, fetcher
  );

  if (!id) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 gap-4 mt-20">
        <IdentificationCard size={64} className="text-slate-300" />
        <p className="font-mono text-sm uppercase tracking-wider">No Subject ID Provided</p>
        <p className="text-xs text-slate-400 max-w-md text-center">Navigate to the Citizen Registry, find a citizen, and click the view icon to open their full dossier.</p>
        <a href="/citizens" className="text-blue-700 font-semibold text-xs border border-blue-700 px-4 py-2 hover:bg-blue-50 mt-4">Open Citizen Registry</a>
      </div>
    );
  }

  if (isLoading) return <div className="text-sm font-mono p-8 uppercase tracking-widest text-slate-500">Retrieving secure dossier...</div>;
  if (profileErr || !profileRes?.success) return <div className="p-8 text-red-700 bg-red-50 border border-red-200 text-sm font-mono font-bold">ERROR: Could not retrieve citizen profile. Check that the backend is running.</div>;

  const c = profileRes.data;
  const auditTrail = c.audit_trail || [];
  const assets = c.assets || { vehicles: [], properties: [], businesses: [], travel: [], utilities: [], total_value: 0 };

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-slate-900">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
            <User size={32} />
            <span>{c.canonical_name || c.name || 'Unknown'}</span>
            {c.urdu_name && !String(c.canonical_name || c.name).includes(c.urdu_name) && (
              <span className="text-2xl text-slate-600 font-normal font-sans tracking-normal" dir="rtl">
                ({c.urdu_name})
              </span>
            )}
          </h1>
          <div className="flex items-center gap-3">
            <a
              href={`/graph?id=${c.citizen_id}`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-sm transition-colors"
            >
              <ShareNetwork size={16} /> Knowledge Graph
            </a>
            <GenerateNoticeButton citizen={c} />
          </div>
        </div>
        <p className="text-sm text-slate-500 font-mono mt-2">
          ID: <span className="font-bold text-slate-900">{c.citizen_id}</span> | CNIC: <span className="font-bold text-slate-900">{c.cnic ? String(c.cnic).replace(/\.0$/, '') : 'N/A'}</span> | Father: <span className="font-bold text-slate-900">{c.father_name || 'N/A'}</span>
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-1 flex flex-col gap-6">
          {/* Risk Profile */}
          <div className="gov-panel p-6 flex flex-col items-center text-center">
            <ShieldWarning size={48} className={c.deviation_score > 75 ? "text-red-700" : c.deviation_score > 40 ? "text-amber-600" : "text-green-600"} />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-4">Deviation Score</span>
            <span className="text-5xl font-bold text-slate-900 mt-2">{(c.deviation_score || 0).toFixed(1)}</span>
            <div className="w-full bg-slate-200 h-2 mt-4 overflow-hidden rounded-full">
              <div className="h-full rounded-full" style={{ width: `${c.deviation_score || 0}%`, backgroundColor: (c.deviation_score || 0) > 75 ? '#dc2626' : (c.deviation_score || 0) > 40 ? '#d97706' : '#16a34a' }}></div>
            </div>
            <span className="text-xs font-bold text-slate-900 uppercase mt-4 px-3 py-1 bg-slate-100 border border-slate-300">
              Category {c.risk_category || 'Unknown'}
            </span>
          </div>

          {/* Demographics */}
          <div className="gov-panel p-0">
            <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900">Subject Details</div>
            <div className="p-4 flex flex-col gap-3 text-sm">
              {c.urdu_name && <DetailRow label="Native Name (اردو)" value={c.urdu_name} />}
              <DetailRow label="City" value={c.city || 'N/A'} />
              <DetailRow label="Province" value={c.province || 'N/A'} />
              <DetailRow label="Phone" value={c.phone ? String(c.phone).replace(/\.0$/, '') : 'N/A'} />
              <DetailRow label="Address" value={c.address || 'N/A'} />
              <DetailRow label="Filing Status" value={c.filing_status || 'N/A'} highlight={c.filing_status !== 'Filer'} />
              <DetailRow label="Data Sources" value={`${c.num_sources || 0} datasets`} />
            </div>
          </div>
        </div>

        <div className="col-span-2 flex flex-col gap-6">
          {/* Financial Summary */}
          <div className="gov-panel p-0">
            <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900">Financial Overview (PKR)</div>
            <div className="p-6 grid grid-cols-2 lg:grid-cols-3 gap-6">
              <FinanceCell label="Declared Income" value={c.declared_income} />
              <FinanceCell label="Tax Paid" value={c.tax_paid} />
              <FinanceCell label="Est. Net Worth" value={c.estimated_net_worth} danger />
              <FinanceCell label="Hidden Income (Est.)" value={c.estimated_hidden_income} danger />
              <FinanceCell label="Recoverable Tax (Est.)" value={c.estimated_recoverable_tax} danger />
              <FinanceCell label="Total Assets" value={assets.total_value} />
            </div>
          </div>

          {/* Audit Trail */}
          <div className="gov-panel p-0">
            <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900">
              System Audit Flags ({auditTrail.length})
            </div>
            <ul className="divide-y divide-slate-200">
              {auditTrail.length === 0 ? (
                <li className="p-6 text-sm text-slate-500 font-mono text-center">NO ANOMALIES DETECTED FOR THIS SUBJECT</li>
              ) : (
                auditTrail.map((flag: any, idx: number) => (
                  <li key={idx} className={`p-4 flex gap-4 items-start ${flag.severity === 'CRITICAL' ? 'bg-red-50/50' : ''}`}>
                    <ShieldWarning size={18} weight="fill" className={flag.severity === 'CRITICAL' ? 'text-red-600' : 'text-amber-500'} />
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold text-slate-900">{flag.description}</span>
                      <span className="text-[10px] font-mono text-slate-500 mt-1 uppercase">SEVERITY: {flag.severity}</span>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      </div>

      {/* ===== AI INVESTIGATION SUMMARY (Category C, D, E only) ===== */}
      {["C", "D", "E"].includes(c.risk_category) && (
        <AISummaryPanel citizenId={c.citizen_id} />
      )}

      {/* ===== DETAILED ASSET TABLES ===== */}

      {/* Vehicles */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <Car size={16} /> Vehicles ({assets.vehicles?.length || 0})
        </div>
        {assets.vehicles?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Registration</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Brand</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Model</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Year</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Engine (cc)</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">City</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase text-right">Market Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.vehicles.map((v: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">{v.car_registration_number || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-700">{v.car_brand || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-700">{v.car_model || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{v.model_year || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{v.engine_size_cc || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{v.city || 'N/A'}</td>
                    <td className="px-4 py-3 font-mono text-right font-semibold text-slate-900">PKR {Number(v.market_value || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO VEHICLE RECORDS FOUND</div>
        )}
      </div>

      {/* Properties */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <House size={16} /> Properties ({assets.properties?.length || 0})
        </div>
        {assets.properties?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Type</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Society</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Plot/House</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Area</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">City</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Year</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase text-right">Market Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.properties.map((p: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">{p.property_type || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-700">{p.society_name || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono">{p.plot_house_no || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{p.area || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{p.city || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{p.purchase_year || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm ${p.ownership_status === 'Owned' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>{p.ownership_status || 'N/A'}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-right font-semibold text-slate-900">PKR {Number(p.market_value || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO PROPERTY RECORDS FOUND</div>
        )}
      </div>

      {/* Businesses */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <Buildings size={16} /> Businesses ({assets.businesses?.length || 0})
        </div>
        {assets.businesses?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Company Name</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Entity Type</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Incorporation</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">City</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Office Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.businesses.map((b: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">{b.company_name || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-700">{b.entity_type || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm ${b.status === 'Active' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>{b.status || 'N/A'}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-mono">{b.incorporation_date || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{b.city || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600 max-w-[200px] truncate" title={b.registered_office_address}>{b.registered_office_address || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO BUSINESS RECORDS FOUND</div>
        )}
      </div>

      {/* Travel Records */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <AirplaneTilt size={16} /> Travel Records ({assets.travel?.length || 0})
        </div>
        {assets.travel?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Passport</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">From</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Destination</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Date</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Visa Type</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.travel.map((t: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-slate-900">{t.passport_no || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-700">{t.travelling_from || 'N/A'}</td>
                    <td className="px-4 py-3 font-semibold text-slate-900">{t.destination || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono">{t.travel_date || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm ${t.visa_type === 'Business' ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-100 text-slate-600 border border-slate-200'}`}>{t.visa_type || 'N/A'}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{t.reason_to_travel || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO TRAVEL RECORDS FOUND</div>
        )}
      </div>

      {/* Utility Bills */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <Lightning size={16} /> Utility Connections ({assets.utilities?.length || 0})
        </div>
        {assets.utilities?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Consumer ID</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Meter No</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Address</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">City</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Province</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.utilities.map((u: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">{u.consumer_id || 'N/A'}</td>
                    <td className="px-4 py-3 font-mono text-slate-700">{u.meter_no || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{u.address || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{u.city || 'N/A'}</td>
                    <td className="px-4 py-3 text-slate-600">{u.province || 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO UTILITY RECORDS FOUND</div>
        )}
      </div>

      {/* Bank Accounts */}
      <div className="gov-panel p-0">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
          <Bank size={16} /> Bank Accounts ({assets.banking?.length || 0})
        </div>
        {assets.banking?.length > 0 ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Bank Name</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Account Last 4</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Account Type</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Monthly Expenditure</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">Annual Expenditure</th>
                  <th className="px-4 py-2 font-semibold text-slate-500 uppercase">City / Province</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {assets.banking.map((b: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">{b.bank_name || 'N/A'}</td>
                    <td className="px-4 py-3 font-mono font-bold text-blue-700">•••• {b.account_last4 || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-sm bg-slate-100 text-slate-700 border border-slate-200">
                        {b.account_type || 'Current'}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-800">
                      PKR {Number(b.monthly_expenditure_pkr || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">
                      PKR {Number(b.annual_expenditure_pkr || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {b.city || 'N/A'}, {b.province || 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-sm text-slate-400 font-mono text-center">NO BANK ACCOUNT RECORDS FOUND</div>
        )}
      </div>

    </div>
  );
}

function DetailRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between border-b border-slate-100 pb-2">
      <span className="text-slate-500 font-semibold">{label}</span>
      <span className={`font-medium ${highlight ? 'text-red-700 font-bold' : 'text-slate-900'}`}>{value}</span>
    </div>
  );
}

function FinanceCell({ label, value, danger = false }: { label: string; value: any; danger?: boolean }) {
  const numVal = typeof value === "number" ? value : 0;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</span>
      <span className={`text-xl font-bold ${danger && numVal > 0 ? 'text-red-700' : 'text-slate-900'}`}>
        {numVal.toLocaleString()}
      </span>
    </div>
  );
}

function AISummaryPanel({ citizenId }: { citizenId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    if (summary) {
      setExpanded(!expanded);
      return;
    }
    setExpanded(true);
    setLoading(true);
    setError(null);
    setSummary('');
    try {
      const res = await fetch(`${API}/api/v1/ai/citizens/${citizenId}/summary?stream=true`);
      if (!res.ok) throw new Error("API Error");
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      
      if (reader) {
        let text = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          text += chunk;
          setSummary(text);
        }
      }
    } catch (e) {
      setError("Unable to reach AI service. Ensure Ollama is running with Qwen2.5-3B.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gov-panel p-0">
      <button
        onClick={fetchSummary}
        className="w-full bg-slate-100 border-b border-slate-300 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center justify-between hover:bg-slate-200 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-teal-700" />
          AI Investigation Summary
          <span className="text-[9px] font-mono text-teal-700 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded">QWEN2.5-3B</span>
        </div>
        <div className="flex items-center gap-2">
          {loading && <CircleNotch size={14} className="animate-spin text-teal-600" />}
          {expanded ? <CaretUp size={14} /> : <CaretDown size={14} />}
        </div>
      </button>
      {expanded && (
        <div className="p-6">
          {loading && (
            <div className="flex items-center gap-3 text-sm text-slate-500 font-mono">
              <CircleNotch size={18} className="animate-spin text-teal-600" />
              <span className="uppercase tracking-widest text-xs">Generating AI analysis...</span>
            </div>
          )}
          {error && (
            <div className="text-sm text-red-600 font-mono bg-red-50 border border-red-200 p-3 rounded">
              {error}
            </div>
          )}
          {summary && (
            <div className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
              {summary}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AuditProfile() {
  return (
    <Suspense fallback={<div className="font-mono text-sm uppercase p-8 text-slate-500">Loading secure environment...</div>}>
      <ProfileContent />
    </Suspense>
  );
}
