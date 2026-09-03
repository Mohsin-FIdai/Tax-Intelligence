"use client";

import { useState, useEffect } from "react";
import { TopNav } from "./TopNav";
import { ShieldCheck, Brain, Target, EnvelopeSimple, LockKey, Eye, EyeClosed, ArrowRight, Database, ChartLine, MapPin } from "@phosphor-icons/react";
import ChatWidget from "./ChatWidget";

// Floating particle component
function Particle({ delay, duration, x }: { delay: number; duration: number; x: number }) {
  return (
    <div
      className="absolute bottom-0 rounded-full pointer-events-none"
      style={{
        left: `${x}%`,
        width: Math.random() * 4 + 2 + "px",
        height: Math.random() * 4 + 2 + "px",
        backgroundColor: `rgba(${Math.random() > 0.5 ? "45,212,191" : "96,165,250"}, 0.6)`,
        animationName: "float-up",
        animationDuration: `${duration}s`,
        animationDelay: `${delay}s`,
        animationTimingFunction: "linear",
        animationIterationCount: "infinite",
      }}
    />
  );
}

// Network node component
function NetworkNode({ x, y, size, delay }: { x: number; y: number; size: number; delay: number }) {
  return (
    <div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: "rgba(45,212,191,0.8)",
        boxShadow: `0 0 ${size * 3}px rgba(45,212,191,0.5)`,
        animationName: "node-pulse",
        animationDuration: "3s",
        animationDelay: `${delay}s`,
        animationTimingFunction: "ease-in-out",
        animationIterationCount: "infinite",
      }}
    />
  );
}

const PARTICLES = Array.from({ length: 20 }, (_, i) => ({
  delay: Math.random() * 8,
  duration: Math.random() * 8 + 6,
  x: Math.random() * 50,
}));

const NODES = [
  { x: 8, y: 25, size: 4, delay: 0 },
  { x: 15, y: 60, size: 3, delay: 1 },
  { x: 25, y: 40, size: 5, delay: 0.5 },
  { x: 35, y: 75, size: 3, delay: 1.5 },
  { x: 42, y: 20, size: 4, delay: 2 },
  { x: 5, y: 80, size: 3, delay: 0.8 },
  { x: 20, y: 85, size: 4, delay: 1.2 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [typedText, setTypedText] = useState("");
  const [scanPos, setScanPos] = useState(0);

  const fullText = "Smarter data. Stronger decisions. A fairer tomorrow.";

  useEffect(() => {
    // Clear localStorage token if it exists (migrating to sessionStorage)
    localStorage.removeItem("tax_intel_auth");
    
    const auth = sessionStorage.getItem("tax_intel_auth");
    if (auth === "admin") setIsAuthenticated(true);
    setIsLoaded(true);
  }, []);

  // Typing effect
  useEffect(() => {
    if (isAuthenticated) return;
    let i = 0;
    const interval = setInterval(() => {
      if (i <= fullText.length) {
        setTypedText(fullText.slice(0, i));
        i++;
      } else {
        clearInterval(interval);
      }
    }, 35);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Scan line animation
  useEffect(() => {
    if (isAuthenticated) return;
    const interval = setInterval(() => {
      setScanPos((p) => (p + 1) % 100);
    }, 40);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    setError("");
    setTimeout(() => {
      if (username === "admin" && password === "admin") {
        sessionStorage.setItem("tax_intel_auth", "admin");
        setIsAuthenticated(true);
        // Direct to Ingestion Hub from Executive Dashboard on fresh login
        if (window.location.pathname === "/") {
          window.location.href = "/ingestion";
        }
      } else {
        setError("Invalid credentials. Access denied.");
      }
      setIsAuthenticating(false);
    }, 1400);
  };

  if (!isLoaded) {
    return (
      <div className="h-screen w-screen bg-[#040d1a] flex flex-col items-center justify-center gap-4">
        <div className="w-10 h-10 border-4 border-teal-900 border-t-teal-400 rounded-full animate-spin"></div>
        <p className="text-teal-400/60 text-xs tracking-widest uppercase font-mono">Initializing Secure Terminal...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen w-full flex relative overflow-hidden font-sans"
        style={{ background: "linear-gradient(135deg, #040d1a 0%, #061a14 35%, #0a2a20 60%, #061a14 80%, #040d1a 100%)" }}>

        {/* ── Animated floating particles (left half only) ── */}
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
          {PARTICLES.map((p, i) => <Particle key={i} {...p} />)}
        </div>

        {/* ── Network nodes ── */}
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
          {NODES.map((n, i) => <NetworkNode key={i} {...n} />)}
          {/* Connection lines between nodes */}
          <svg className="absolute inset-0 w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
            <line x1="8%" y1="25%" x2="25%" y2="40%" stroke="#2dd4bf" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="25%" y1="40%" x2="15%" y2="60%" stroke="#2dd4bf" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="15%" y1="60%" x2="35%" y2="75%" stroke="#2dd4bf" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="35%" y1="75%" x2="42%" y2="20%" stroke="#2dd4bf" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="42%" y1="20%" x2="25%" y2="40%" stroke="#2dd4bf" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="5%" y1="80%" x2="20%" y2="85%" stroke="#60a5fa" strokeWidth="0.5" strokeDasharray="4,4" />
            <line x1="20%" y1="85%" x2="35%" y2="75%" stroke="#60a5fa" strokeWidth="0.5" strokeDasharray="4,4" />
          </svg>
        </div>

        {/* ── Dark wave bottom-left ── */}
        <div className="absolute bottom-0 left-0 w-[60vw] h-[75vh] z-0 pointer-events-none">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
            <path d="M0,100 L0,45 C20,85 50,30 100,100 Z" fill="#022119" opacity="0.95" />
            <path d="M0,100 L0,65 C35,92 55,65 100,100 Z" fill="#0b5443" opacity="0.55" />
            <path d="M0,100 L0,80 C50,98 70,82 100,100 Z" fill="#0d6b54" opacity="0.3" />
          </svg>
        </div>

        {/* ── Right globe rings ── */}
        <div className="absolute inset-0 w-full h-screen z-0 pointer-events-none overflow-hidden">
          <div className="absolute -right-32 top-[8%] w-[700px] h-[700px] rounded-full border border-dashed border-teal-400/20 animate-orbit" />
          <div className="absolute -right-16 top-[18%] w-[520px] h-[520px] rounded-full border border-dotted border-blue-300/25 animate-orbit-reverse" />
          <div className="absolute -right-8 top-[28%] w-[360px] h-[360px] rounded-full border border-teal-500/15" />
          {/* Globe highlight dots */}
          <div className="absolute right-[18%] top-[22%] w-2 h-2 rounded-full bg-teal-400 shadow-[0_0_12px_rgba(45,212,191,0.9)]" style={{ animationName: "node-pulse", animationDuration: "2.5s", animationIterationCount: "infinite" }} />
          <div className="absolute right-[32%] top-[55%] w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.9)]" style={{ animationName: "node-pulse", animationDuration: "3.5s", animationDelay: "1s", animationIterationCount: "infinite" }} />
          <div className="absolute right-[10%] top-[65%] w-2 h-2 rounded-full bg-teal-300 shadow-[0_0_12px_rgba(94,234,212,0.9)]" style={{ animationName: "node-pulse", animationDuration: "4s", animationDelay: "0.5s", animationIterationCount: "infinite" }} />
          {/* Connecting arcs */}
          <svg className="absolute inset-0 w-full h-full opacity-15">
            <path d="M80%,20% Q60%,50% 85%,75%" fill="none" stroke="#2dd4bf" strokeWidth="0.8" />
          </svg>
        </div>

        {/* ── Horizontal scan line on left ── */}
        <div className="absolute left-0 w-[50%] h-[1px] z-0 pointer-events-none"
          style={{ top: `${scanPos}%`, background: "linear-gradient(to right, transparent, rgba(45,212,191,0.15), transparent)" }} />

        {/* ── TOP CORNER LABELS ── */}
        <div className="absolute top-8 left-10 text-[9px] font-bold tracking-[0.25em] text-teal-400/70 uppercase flex items-center gap-3 z-20">
          <span className="w-8 h-[1px] bg-teal-400/50"></span>
          FEDERAL TAX INTELLIGENCE
        </div>
        <div className="absolute top-8 right-10 text-[9px] font-bold tracking-[0.25em] text-slate-400/70 uppercase flex items-center gap-3 z-20">
          <span className="w-8 h-[1px] bg-slate-400/50"></span>
          DATA / INSIGHTS / ACTION
        </div>



        {/* ── LIVE STATUS BAR ── */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-6 text-[8px] font-mono tracking-widest text-white/30 uppercase">
          <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> System Online</span>
          <span>|</span>
          <span className="flex items-center gap-1.5"><ChartLine size={9} /> Real-time data</span>
          <span>|</span>
          <span className="flex items-center gap-1.5"><Database size={9} /> 6,247 Records</span>
          <span>|</span>
          <span className="flex items-center gap-1.5"><MapPin size={9} /> Pakistan</span>
        </div>

        {/* ── MAIN CONTENT ── */}
        <div className="relative z-10 flex w-full max-w-[1600px] mx-auto min-h-screen items-center justify-evenly px-12">

          {/* LEFT: Branding */}
          <div className="flex flex-col items-center justify-center -mt-20">

            {/* Logo */}
            <div className="animate-fade-in-up anim-delay-100 -mb-10 relative z-20">
              {/* Subtle radial glow behind logo for contrast */}
              <div className="absolute inset-0 -m-10 rounded-full pointer-events-none"
                style={{ background: "radial-gradient(ellipse at center, rgba(255,255,255,0.12) 0%, transparent 65%)" }} />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/logo.png?v=3"
                alt="Federal Tax Intelligence"
                className="h-[270px] w-auto object-contain relative z-10"
                style={{
                  background: "transparent",
                  border: "none",
                  boxShadow: "none",
                  filter: "brightness(2) contrast(1.2) saturate(1.5) drop-shadow(0 0 25px rgba(255,255,255,0.6)) drop-shadow(0 0 50px rgba(45,212,191,0.8)) drop-shadow(0 12px 30px rgba(0,0,0,0.8))"
                }}
              />
            </div>

            {/* Tagline */}
            <div className="animate-fade-in-up anim-delay-200 flex items-center gap-2.5 text-[11px] font-black tracking-[0.3em] text-white uppercase mb-4">
              <span className="drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">DETECT</span>
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shadow-[0_0_10px_rgba(45,212,191,1)]"></span>
              <span className="drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">ANALYZE</span>
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shadow-[0_0_10px_rgba(45,212,191,1)]"></span>
              <span className="drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]">ENFORCE</span>
            </div>

            {/* Jinnah Quote */}
            <div className="animate-fade-in-up anim-delay-300 flex flex-col items-center justify-center opacity-80 hover:opacity-100 transition-opacity duration-1000 max-w-[500px] text-center mt-6">
              <p className="text-[12px] font-serif italic text-white/90 tracking-wider leading-loose drop-shadow-md">
                “One of the biggest curses from which India is suffering … is bribery and corruption. That really is a poison. We must put that down with an iron hand.”
              </p>
              <p className="text-[9px] font-bold tracking-[0.25em] text-teal-300 mt-4 uppercase drop-shadow-md">
                Muhammad Ali Jinnah
              </p>
            </div>


          </div>

          {/* RIGHT: Login Card */}
          <div className="animate-fade-in-up anim-delay-300 flex justify-center items-center px-12">
            
            {/* Wrapper for card + glow */}
            <div className="relative">
              {/* Outer glow ring */}
              <div className="absolute inset-0 rounded-2xl animate-pulse-glow pointer-events-none -m-1.5"></div>

              <div className="w-[340px] rounded-2xl p-7 relative overflow-hidden"
                style={{
                  background: "rgba(255,255,255,0.97)",
                  backdropFilter: "blur(20px)",
                  boxShadow: "0 20px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,1)",
                  border: "1px solid rgba(255,255,255,0.9)",
                }}>
                
                {/* Header */}
                <div className="mb-6 flex justify-between items-center">
                  <span className="text-[9px] font-bold tracking-widest text-slate-400 uppercase">Classified System</span>
                  <div className="flex items-center gap-1 text-emerald-600 text-[8px] font-bold uppercase tracking-wider bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100">
                    <ShieldCheck size={12} weight="fill" /> Secure Access
                  </div>
                </div>

                <form onSubmit={handleLogin} className="space-y-5">
                  <div className="space-y-1.5">
                    <label className="block text-[9px] font-bold text-slate-400 uppercase tracking-widest ml-1">Agent ID</label>
                    <div className="relative flex items-center group">
                      <EnvelopeSimple size={14} className="absolute left-3 text-slate-400 group-focus-within:text-teal-600 transition-colors z-10" />
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 pl-9 pr-3 py-2.5 rounded-lg text-slate-800 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-teal-400/40 focus:border-teal-400 focus:bg-white transition-all placeholder:text-slate-300"
                        placeholder="agent@fti.gov.pk"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-[9px] font-bold text-slate-400 uppercase tracking-widest ml-1">Passkey</label>
                    <div className="relative flex items-center group">
                      <LockKey size={14} className="absolute left-3 text-slate-400 group-focus-within:text-teal-600 transition-colors z-10" />
                      <input
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 pl-9 pr-9 py-2.5 rounded-lg text-slate-800 text-lg font-mono tracking-[0.25em] focus:outline-none focus:ring-2 focus:ring-teal-400/40 focus:border-teal-400 focus:bg-white transition-all placeholder:text-slate-300 placeholder:text-base placeholder:tracking-normal placeholder:font-sans"
                        placeholder="••••••"
                        required
                      />
                      <button type="button" onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 text-slate-400 hover:text-slate-600 transition-colors focus:outline-none z-10">
                        {showPassword ? <Eye size={14} /> : <EyeClosed size={14} />}
                      </button>
                    </div>
                  </div>

                  {error && (
                    <div className="animate-fade-in flex items-center gap-2 bg-red-50 border border-red-100 text-red-600 text-[9px] font-medium px-3 py-2 rounded-lg mt-2">
                      <span className="w-1 h-1 rounded-full bg-red-500 flex-shrink-0"></span>
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isAuthenticating}
                    className="w-full text-white font-bold py-3 rounded-lg text-[10px] tracking-[0.2em] uppercase transition-all duration-300 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
                    style={{
                      background: isAuthenticating
                        ? "linear-gradient(135deg, #07241f, #0a352d)"
                        : "linear-gradient(135deg, #07241f 0%, #0f4a3a 50%, #07241f 100%)",
                      boxShadow: "0 8px 30px rgba(7,36,31,0.5), inset 0 1px 0 rgba(255,255,255,0.1)",
                    }}
                  >
                    {isAuthenticating ? (
                      <span className="flex items-center gap-2">
                        <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                        AUTHENTICATING...
                      </span>
                    ) : (
                      <>
                        INITIATE SECURE SESSION
                        <ArrowRight size={12} weight="bold" />
                      </>
                    )}
                  </button>
                </form>

                {/* Footer status */}
                <div className="mt-6 pt-4 border-t border-slate-100 flex justify-between items-center">
                  <div className="flex items-center gap-1.5 text-[7px] text-slate-400 font-mono uppercase tracking-widest">
                    <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse"></span>
                    SYSTEM ONLINE
                  </div>
                  <div className="text-[7px] text-slate-300 font-mono uppercase tracking-widest">
                    SECURE ENCLAVE v2.1
                  </div>
                </div>
              </div>
            </div>
            {/* End wrapper */}
          </div>
        </div>
      </div>
    );
  }

  // Authenticated: full app
  return (
    <>
      <header className="h-14 bg-[#0f172a] text-white flex items-center justify-between px-6 shadow-md z-20 relative">
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center border-2 border-slate-400/50 overflow-hidden p-0.5 shadow-[0_0_15px_rgba(45,212,191,0.2)]">
            <img src="/logo-icon.png" alt="FTI Logo" className="w-full h-full object-contain" />
          </div>
          <span className="font-semibold tracking-wide text-sm uppercase">Federal Tax Intelligence System</span>
        </div>
        <div className="text-xs text-slate-400 flex items-center gap-4 font-mono">
          <span>OFFICIAL USE ONLY</span>
          <span>|</span>
          <span>AGENT ID: ADMIN</span>
          <span>|</span>
          <span>SECURE TERMINAL</span>
          <button
            onClick={() => { localStorage.removeItem("tax_intel_auth"); setIsAuthenticated(false); }}
            className="ml-4 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
          >
            LOGOUT
          </button>
        </div>
      </header>

      <TopNav />

      <main className="flex-1 overflow-y-auto p-8 relative z-0">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
      
      <ChatWidget />
    </>
  );
}
