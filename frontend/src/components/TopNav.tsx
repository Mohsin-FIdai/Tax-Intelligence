"use client";

import { useState, useRef, useEffect } from "react";

export function TopNav() {
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const toggleMenu = (menu: string) => {
    setOpenMenu(openMenu === menu ? null : menu);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (!(e.target as Element).closest('.nav-dropdown-container')) {
        setOpenMenu(null);
      }
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  return (
    <nav className="h-12 bg-white border-b border-slate-300 flex items-center px-6 shadow-sm z-10 space-x-6">
      <DropdownMenu 
        title="System" 
        isOpen={openMenu === "System"} 
        onClick={() => toggleMenu("System")}
      >
        <DropdownItem href="/ingestion">Data Ingestion Hub</DropdownItem>
      </DropdownMenu>

      <DropdownMenu 
        title="Overview" 
        isOpen={openMenu === "Overview"} 
        onClick={() => toggleMenu("Overview")}
      >
        <DropdownItem href="/" active>Executive Dashboard</DropdownItem>
        <DropdownItem href="/map">Geographic Heat Maps</DropdownItem>
      </DropdownMenu>

      <DropdownMenu 
        title="Analysis" 
        isOpen={openMenu === "Analysis"} 
        onClick={() => toggleMenu("Analysis")}
      >
        <DropdownItem href="/resolution">Entity Resolution</DropdownItem>
        <DropdownItem href="/graph">Knowledge Graph</DropdownItem>
        <DropdownItem href="/networks">Hidden Networks</DropdownItem>
        <DropdownItem href="/risk">Risk Analytics</DropdownItem>
      </DropdownMenu>

      <a href="/chat" className="text-sm font-semibold transition-colors text-slate-600 hover:text-slate-900 flex items-center gap-1">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M208,88h-8V64a16,16,0,0,0-16-16H72A16,16,0,0,0,56,64V88H48A16,16,0,0,0,32,104v48a16,16,0,0,0,16,16h8v24a16,16,0,0,0,16,16H184a16,16,0,0,0,16-16V168h8a16,16,0,0,0,16-16V104A16,16,0,0,0,208,88ZM72,64H184V88H72ZM48,152V104h8v48Zm136,40H72V152h48a16,16,0,0,0,16-16,8,8,0,0,1,16,0,16,16,0,0,0,16,16h16Zm24-40h-8V104h8v48Z"></path></svg>
        AI Assistant
      </a>

      <a href="/citizens" className="text-sm font-semibold transition-colors text-slate-600 hover:text-slate-900">
        Citizen Registry
      </a>
    </nav>
  );
}

function DropdownMenu({ title, isOpen, onClick, children }: { title: string, isOpen: boolean, onClick: () => void, children: React.ReactNode }) {
  return (
    <div className="relative nav-dropdown-container">
      <button 
        onClick={onClick}
        className={`text-sm font-semibold flex items-center gap-1 transition-colors ${isOpen ? 'text-blue-700' : 'text-slate-600 hover:text-slate-900'}`}
      >
        {title}
        <svg className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-56 bg-white border border-slate-200 shadow-lg rounded-sm py-1 z-50 flex flex-col">
          {children}
        </div>
      )}
    </div>
  );
}

function DropdownItem({ href, children, active = false }: { href: string; children: React.ReactNode; active?: boolean }) {
  return (
    <a 
      href={href} 
      className={`px-4 py-2 text-sm transition-colors flex items-center gap-2 ${
        active 
          ? "bg-slate-50 text-blue-700 font-medium border-l-2 border-blue-700" 
          : "text-slate-700 hover:bg-slate-50 border-l-2 border-transparent"
      }`}
    >
      {children}
    </a>
  );
}
