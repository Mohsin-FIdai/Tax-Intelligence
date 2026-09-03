"use client";

import { HandPalm } from "@phosphor-icons/react";

export default function InvestigationCenter() {
  return (
    <div className="flex flex-col gap-6 h-full">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Investigation Center</h1>
        <p className="text-sm text-slate-500">Advanced querying, cross-referencing, and bulk enforcement actions.</p>
      </header>
      <div className="gov-panel p-16 flex flex-col items-center justify-center text-center">
        <HandPalm size={48} className="text-slate-400 mb-4" />
        <h2 className="text-lg font-bold text-slate-900 uppercase tracking-widest">Advanced Query Interface</h2>
        <p className="text-sm text-slate-500 mt-2 max-w-md">
          Use the <strong>Citizen Registry</strong> for standard lookups. The Advanced Investigation Center provides bulk operations and cross-referencing tools.
        </p>
        <a href="/citizens" className="mt-6 bg-blue-700 text-white px-6 py-2 text-sm font-bold uppercase tracking-wider hover:bg-blue-800 transition-colors">
          Open Citizen Registry
        </a>
      </div>
    </div>
  );
}
