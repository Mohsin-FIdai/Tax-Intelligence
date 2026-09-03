"use client";

import React, { useState, useRef, useEffect } from "react";
import { PaperPlaneRight, CaretDown, Sparkle, CircleNotch } from "@phosphor-icons/react";
import { usePathname } from "next/navigation";

import ReactMarkdown from "react-markdown";

import AnimatedLumi from "./AnimatedLumi";

const API = "http://127.0.0.1:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
}

function LumiAvatar({ isThinking, large }: { isThinking?: boolean, large?: boolean }) {
  const size = large ? "w-16 h-16" : "w-10 h-10"; // Slightly larger to fit the animated character better

  return (
    <div className={`relative flex items-center justify-center ${size}`}>
      {/* Outer glow */}
      <div className={`absolute inset-0 bg-blue-500 rounded-full blur-md opacity-40 ${isThinking ? 'animate-ping' : 'animate-pulse'}`}></div>
      {/* Orb body */}
      <div className={`relative rounded-full w-full h-full shadow-[0_0_15px_rgba(59,130,246,0.5)] flex items-center justify-center overflow-hidden border-2 border-blue-400/50 bg-slate-900 ${isThinking ? 'animate-bounce' : ''}`} style={{ animationDuration: isThinking ? '0.6s' : '2s' }}>
        <AnimatedLumi isThinking={isThinking} className="w-[120%] h-[120%] translate-y-1" />
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi there! I am Lumi ✦ your Tax Intelligence AI.\n\nHow can I help you investigate today?" }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, isOpen]);

  const citizenMatch = pathname?.match(/\/profile\/(.+)/);
  const citizenId = citizenMatch ? citizenMatch[1] : undefined;

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, citizen_id: citizenId, stream: true }),
      });

      if (!res.ok) throw new Error("API Error");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      if (reader) {
        let text = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          text += chunk;
          setMessages((prev) => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].content = text;
            return newMessages;
          });
        }
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Oops! I couldn't reach the AI backend." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = (action: string) => {
    setInput(action);
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3 group">
        <div className="bg-slate-900 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity translate-y-2 group-hover:translate-y-0 duration-300">
          Need help? Ask Lumi!
        </div>
        <button
          onClick={() => setIsOpen(true)}
          className="bg-slate-900 p-3 rounded-full shadow-[0_0_15px_rgba(45,212,191,0.4)] hover:shadow-[0_0_25px_rgba(45,212,191,0.6)] transition-all hover:-translate-y-1 flex items-center justify-center border-2 border-slate-700"
          title="Open Lumi AI"
        >
          <LumiAvatar large />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80 sm:w-96 h-[550px] max-h-[85vh] bg-slate-50 border border-slate-300 shadow-2xl rounded-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 fade-in duration-300">
      {/* Header */}
      <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-3">
          <LumiAvatar />
          <div className="flex flex-col">
            <span className="font-black text-sm tracking-widest uppercase flex items-center gap-1 text-teal-400">LUMI <Sparkle size={12} weight="fill" /></span>
            <span className="text-[9px] font-mono text-slate-400">QWEN2.5-3B NEURAL CORE</span>
          </div>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white transition-colors bg-slate-800 p-1.5 rounded-full">
          <CaretDown size={16} weight="bold" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            {msg.role === "assistant" && (
              <span className="text-[9px] font-bold text-teal-600 uppercase mb-1 ml-1 flex items-center gap-1">
                <Sparkle size={10} /> Lumi
              </span>
            )}
            <div
              className={`p-3 text-sm max-w-[90%] shadow-sm ${
                msg.role === "user"
                  ? "bg-slate-900 text-white rounded-2xl rounded-tr-sm"
                  : "bg-white border border-slate-200 text-slate-700 rounded-2xl rounded-tl-sm"
              }`}
            >
              {msg.role === "user" ? (
                msg.content
              ) : (
                <div className="prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown
                    components={{
                      p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                      ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2" {...props} />,
                      strong: ({node, ...props}) => <strong className="font-bold text-slate-900" {...props} />
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex flex-col items-start">
            <span className="text-[9px] font-bold text-teal-600 uppercase mb-1 ml-1 flex items-center gap-1">
              <Sparkle size={10} /> Lumi
            </span>
            <div className="p-3 bg-white border border-slate-200 text-teal-600 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-3">
              <LumiAvatar isThinking />
              <span className="text-xs font-mono uppercase tracking-widest opacity-70 animate-pulse">Analyzing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Quick Automations */}
      {messages.length === 1 && !isLoading && (
        <div className="px-4 pb-2 flex gap-2 overflow-x-auto no-scrollbar scrollbar-hide">
          <button onClick={() => handleQuickAction("What are the most critical flags in the system right now?")} className="shrink-0 text-[10px] font-bold uppercase tracking-wider bg-teal-50 text-teal-700 border border-teal-200 px-3 py-1.5 rounded-full hover:bg-teal-100 transition-colors">Find Critical Flags</button>
          <button onClick={() => handleQuickAction("Explain how the deviation score is calculated.")} className="shrink-0 text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-full hover:bg-indigo-100 transition-colors">Explain Risk Score</button>
          {citizenId && <button onClick={() => handleQuickAction(`Generate a full audit report for ${citizenId}`)} className="shrink-0 text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200 px-3 py-1.5 rounded-full hover:bg-rose-100 transition-colors">Audit {citizenId}</button>}
        </div>
      )}

      {/* Input */}
      <form onSubmit={sendMessage} className="p-3 bg-white border-t border-slate-200 flex items-end gap-2">
        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendMessage(e as any);
            }
          }}
          placeholder={citizenId ? `Ask Lumi about ${citizenId}...` : "Ask Lumi a question..."}
          className="flex-1 resize-none bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-teal-500 max-h-32 shadow-inner"
          style={{ minHeight: "44px" }}
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="bg-teal-500 text-white p-3 rounded-xl hover:bg-teal-600 shadow-[0_0_10px_rgba(20,184,166,0.3)] disabled:shadow-none disabled:bg-slate-300 disabled:text-slate-500 transition-all flex-shrink-0"
        >
          <PaperPlaneRight size={18} weight="fill" />
        </button>
      </form>
    </div>
  );
}
