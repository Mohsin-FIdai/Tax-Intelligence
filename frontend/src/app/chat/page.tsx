"use client"

import { useState, useRef, useEffect } from 'react'
import { ChatCircleDots, PaperPlaneTilt, Clock, BookmarkSimple, ShieldWarning, ShieldCheck, Link, FileText, MagnifyingGlass, LockKey, User, CircleNotch, EnvelopeSimple, CaretLeft } from '@phosphor-icons/react'
import ReactMarkdown from 'react-markdown'
import AnimatedLumi from '@/components/AnimatedLumi'

const API = 'http://127.0.0.1:8000'

interface Message {
  role: 'assistant' | 'user';
  content: string;
}

export default function ChatPage() {
  const defaultMessage: Message = { role: 'assistant', content: 'Hello! I\'m Lumi, your AI Intelligence Assistant.\n\nI can help you with tax intelligence, entity resolution, risk assessment, pattern analysis, and more.\n\nHow can I assist your investigation today?' };
  
  const [messages, setMessages] = useState<Message[]>([defaultMessage]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [citizenId, setCitizenId] = useState('');
  const [activeTab, setActiveTab] = useState<'home' | 'chat' | 'history' | 'request_info'>('home');
  
  const [reqCnic, setReqCnic] = useState('');
  const [reqName, setReqName] = useState('');
  const [reqOrg, setReqOrg] = useState('NADRA');
  const [reqLoading, setReqLoading] = useState(false);
  const [reqStatus, setReqStatus] = useState<{type: 'idle' | 'success' | 'error', message: string}>({type: 'idle', message: ''});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, activeTab]);

  const handleNewConversation = () => {
    setMessages([defaultMessage]);
    setCitizenId('');
    setActiveTab('chat');
  };

  const sendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, citizen_id: citizenId || undefined, stream: true })
      });
      
      if (!res.ok) throw new Error('API Error');
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
      
      if (reader) {
        let text = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          text += chunk;
          setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].content = text;
            return newMessages;
          });
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Unable to reach AI backend. Please verify system connectivity.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchCitizen = async () => {
    if (!reqCnic.trim()) return;
    setReqLoading(true);
    setReqStatus({ type: 'idle', message: '' });
    try {
      const res = await fetch(`${API}/api/v1/citizens?search_query=${reqCnic}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (data.data && data.data.length > 0) {
        setReqName(data.data[0].canonical_name || data.data[0].full_name || 'Name not found in DB');
        setReqStatus({ type: 'success', message: 'Citizen located.' });
      } else {
        setReqName('No records found for this CNIC.');
        setReqStatus({ type: 'error', message: 'Citizen not found in database.' });
      }
    } catch (err) {
      setReqName('Error fetching data.');
      setReqStatus({ type: 'error', message: 'Failed to connect to database.' });
    } finally {
      setReqLoading(false);
    }
  };

  const handleSendEmail = async () => {
    if (!reqCnic.trim() || !reqName.trim()) return;
    setReqLoading(true);
    setReqStatus({ type: 'idle', message: 'Generating PDF and sending email...' });
    
    try {
      const res = await fetch(`${API}/api/v1/email/request-info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cnic: reqCnic,
          citizen_name: reqName,
          organization: reqOrg,
          recipient: "fidaimohsin04@gmail.com",
          sender: "fidaimohsin@gmail.com"
        })
      });
      
      if (!res.ok) throw new Error();
      
      setReqStatus({ type: 'success', message: `Information Request PDF sent successfully to ${reqOrg} (fidaimohhsin04@gmail.com).` });
      
    } catch (err) {
      setReqStatus({ type: 'error', message: 'Failed to send email request. Please try again later.' });
    } finally {
      setReqLoading(false);
    }
  };

  const handleQuickAction = (action: string) => {
    setInput(action);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-50">
      
      {/* Top Header */}
      <div className="bg-white border-b border-slate-200 shadow-sm z-10 relative flex justify-center">
        <div className="flex items-center justify-between px-8 py-6 max-w-7xl w-full">
          <div className="flex items-center gap-6">
            <AnimatedLumi className="w-20 h-20" />
            <div className="flex flex-col justify-center">
              <h1 className="text-3xl font-black tracking-tight text-slate-900 uppercase">
                AI INTELLIGENCE ASSISTANT
              </h1>
              <p className="text-xs text-slate-500 font-mono tracking-widest uppercase mt-1">
                Powered by QWEN2.5-3B | Secure Enclave Interface
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-5 py-2 bg-teal-50 border border-teal-100 rounded-full shadow-inner">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-500 animate-pulse shadow-[0_0_8px_rgba(20,184,166,0.6)]"></span>
            <span className="text-xs font-black text-teal-700 uppercase tracking-widest">LUMI ONLINE</span>
          </div>
        </div>
      </div>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden p-6 max-w-7xl mx-auto w-full">
        
        {/* Dynamic Main Interface */}
        <div className="flex-1 flex flex-col bg-[#040d1a] rounded-2xl border border-slate-800 shadow-2xl overflow-hidden relative">
          
          {activeTab === 'home' && (
            <div className="flex-1 flex flex-col items-center justify-center bg-slate-900/50 p-8">
              <div className="flex flex-col items-center mb-16">
                <div className="w-24 h-24 bg-teal-500/10 rounded-full flex items-center justify-center mb-8 ring-4 ring-teal-500/20">
                   <ChatCircleDots size={48} className="text-teal-400" />
                </div>
                <h2 className="text-3xl font-black text-white tracking-widest uppercase mb-4">Federal Tax Intelligence</h2>
                <p className="text-slate-400 font-mono text-sm max-w-lg text-center">Select an action to proceed with your investigation.</p>
              </div>
              
              <div className="flex gap-8 w-full max-w-3xl">
                <button 
                  onClick={() => setActiveTab('chat')}
                  className="flex-1 bg-slate-900 border border-slate-700 hover:border-teal-500/50 p-10 rounded-2xl flex flex-col items-center justify-center gap-6 transition-all hover:-translate-y-1 hover:shadow-xl group cursor-pointer"
                >
                  <div className="bg-slate-800 p-6 rounded-full group-hover:bg-teal-500/10 transition-colors">
                    <ChatCircleDots size={48} className="text-slate-300 group-hover:text-teal-400 transition-colors" />
                  </div>
                  <span className="text-white font-black tracking-widest uppercase text-lg">Talk to Lumi</span>
                  <span className="text-slate-500 text-xs font-mono text-center">Open the AI Assistant to analyze citizens and detect risks.</span>
                </button>

                <button 
                  onClick={() => setActiveTab('request_info')}
                  className="flex-1 bg-slate-900 border border-slate-700 hover:border-teal-500/50 p-10 rounded-2xl flex flex-col items-center justify-center gap-6 transition-all hover:-translate-y-1 hover:shadow-xl group cursor-pointer"
                >
                  <div className="bg-slate-800 p-6 rounded-full group-hover:bg-teal-500/10 transition-colors">
                    <EnvelopeSimple size={48} className="text-slate-300 group-hover:text-teal-400 transition-colors" />
                  </div>
                  <span className="text-white font-black tracking-widest uppercase text-lg">Email Inquiry</span>
                  <span className="text-slate-500 text-xs font-mono text-center">Send formal information requests to NADRA, IESCO, etc.</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === 'request_info' && (
            <div className="flex-1 flex flex-col p-8 overflow-y-auto">
              <div className="flex items-center gap-4 mb-8 border-b border-slate-800 pb-4">
                <button 
                  onClick={() => setActiveTab('home')}
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
                  title="Back to Home"
                >
                  <CaretLeft size={24} weight="bold" />
                </button>
                <EnvelopeSimple size={32} className="text-teal-500" />
                <div className="flex flex-col">
                  <h3 className="text-2xl font-black text-white tracking-widest uppercase flex items-center gap-2">
                    Request Information
                  </h3>
                  <p className="text-slate-400 text-xs font-mono">Send PDF details request to external organizations (NADRA, IESCO, TEXCIS)</p>
                </div>
              </div>

              <div className="max-w-2xl flex flex-col gap-6">
                <div className="flex flex-col gap-2">
                  <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">Citizen CNIC</label>
                  <div className="flex gap-3">
                    <input 
                      type="text" 
                      value={reqCnic}
                      onChange={(e) => setReqCnic(e.target.value)}
                      placeholder="e.g. 12345-6789012-3"
                      className="flex-1 bg-slate-900/50 border border-slate-700 text-slate-200 px-4 py-3 rounded-xl focus:outline-none focus:border-teal-500/50 transition-colors"
                    />
                    <button 
                      onClick={handleFetchCitizen}
                      disabled={reqLoading || !reqCnic.trim()}
                      className="bg-slate-800 hover:bg-slate-700 text-teal-400 px-6 py-3 rounded-xl font-bold text-sm tracking-widest uppercase transition-colors disabled:opacity-50"
                    >
                      {reqLoading ? 'Fetching...' : 'Fetch Details'}
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">Citizen Name (Autofilled)</label>
                  <input 
                    type="text" 
                    value={reqName}
                    readOnly
                    placeholder="Fetch details to load name..."
                    className="w-full bg-slate-900/30 border border-slate-800 text-slate-400 px-4 py-3 rounded-xl cursor-not-allowed"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-slate-400 text-xs font-bold tracking-widest uppercase">Target Organization</label>
                  <select 
                    value={reqOrg}
                    onChange={(e) => setReqOrg(e.target.value)}
                    className="w-full bg-slate-900/50 border border-slate-700 text-slate-200 px-4 py-3 rounded-xl focus:outline-none focus:border-teal-500/50 transition-colors appearance-none"
                  >
                    <option value="NADRA">NADRA (National Database & Registration Authority)</option>
                    <option value="SBP">State Bank of Pakistan (SBP)</option>
                    <option value="SECP">Securities & Exchange Commission of Pakistan (SECP)</option>
                    <option value="PTA">Pakistan Telecommunication Authority (PTA)</option>
                    <option value="BOR">Provincial Boards of Revenue (Properties)</option>
                    <option value="FBR">Federal Board of Revenue (FBR)</option>
                    <option value="FIA">Federal Investigation Agency (FIA)</option>
                    <option value="WAPDA">WAPDA (Water and Power Development Authority)</option>
                    <option value="EXCISE">Excise & Taxation</option>
                  </select>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 mt-2">
                  <p className="text-slate-400 text-xs mb-3 font-mono">Routing Configuration (Prototype Mode):</p>
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-500">Sender Email:</span>
                      <span className="text-teal-400 font-mono">fidaimohsin@gmail.com</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-500">Recipient Email:</span>
                      <span className="text-teal-400 font-mono">fidaimohsin04@gmail.com</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-500">Attachment:</span>
                      <span className="text-slate-300 font-mono">Information_Request_{reqCnic || 'CNIC'}.pdf</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-col gap-4">
                  <button 
                    onClick={handleSendEmail}
                    disabled={reqLoading || !reqCnic.trim() || !reqName.trim()}
                    className="w-full bg-teal-600 hover:bg-teal-500 text-white px-6 py-4 rounded-xl font-black text-sm tracking-widest uppercase transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {reqLoading ? <CircleNotch size={20} className="animate-spin" /> : <PaperPlaneTilt size={20} weight="fill" />}
                    Send Information Request PDF
                  </button>

                  {reqStatus.message && (
                    <div className={`p-4 rounded-xl text-sm flex items-center gap-3 ${
                      reqStatus.type === 'success' ? 'bg-teal-900/30 text-teal-300 border border-teal-500/30' :
                      reqStatus.type === 'error' ? 'bg-rose-900/30 text-rose-300 border border-rose-500/30' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {reqStatus.type === 'success' && <ShieldCheck size={20} />}
                      {reqStatus.type === 'error' && <ShieldWarning size={20} />}
                      {reqStatus.message}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'chat' && (
            <>
              <div className="px-6 py-4 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 flex justify-between items-center z-10 shadow-sm">
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => setActiveTab('home')}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-md transition-colors"
                    title="Back to Home"
                  >
                    <CaretLeft size={16} weight="bold" />
                  </button>
                  <div className="flex items-center gap-2 text-teal-400 font-mono text-[10px] uppercase tracking-widest font-bold drop-shadow">
                    <ShieldCheck size={16} /> SECURE COMMUNICATIONS CHANNEL
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-slate-500 font-mono text-[10px] uppercase tracking-widest font-bold">CONTEXT ID:</span>
                  <input
                    type="text"
                    value={citizenId}
                    onChange={(e) => setCitizenId(e.target.value)}
                    placeholder="e.g. CZ-12345"
                    className="bg-slate-900/50 border border-slate-700 text-slate-300 px-3 py-1.5 focus:outline-none focus:border-teal-500/50 transition-colors rounded-lg placeholder:text-slate-600 text-xs w-48 shadow-inner"
                  />
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 scroll-smooth">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex max-w-[85%] gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      
                      <div className="flex-shrink-0 mt-2">
                        {msg.role === 'user' ? (
                          <div className="w-10 h-10 rounded-full bg-slate-800 border-2 border-slate-700 flex items-center justify-center text-slate-400 shadow-lg">
                            <User size={20} weight="fill" />
                          </div>
                        ) : (
                          <AnimatedLumi isThinking={idx === messages.length - 1 && isLoading} className="w-12 h-12 bg-slate-900 rounded-full border border-teal-500/30 shadow-[0_0_15px_rgba(45,212,191,0.15)] overflow-hidden" />
                        )}
                      </div>
                      
                      <div className="flex flex-col gap-1.5">
                        {msg.role === 'assistant' && (
                          <div className="flex items-center gap-2 px-1">
                            <span className="text-teal-400 font-black text-[11px] tracking-widest drop-shadow-sm">LUMI</span>
                            <span className="text-slate-600 text-[9px] font-mono tracking-widest">{(new Date()).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                          </div>
                        )}
                        <div 
                          className={`px-6 py-4 shadow-xl ${
                            msg.role === 'user' 
                              ? 'bg-slate-800/90 border border-slate-700/50 text-slate-200 rounded-2xl rounded-tr-sm backdrop-blur-sm' 
                              : 'bg-slate-900/60 border border-slate-800/50 text-slate-300 rounded-2xl rounded-tl-sm backdrop-blur-sm'
                          }`}
                        >
                          {msg.role === 'user' ? (
                            <div className="text-sm whitespace-pre-wrap leading-relaxed font-medium">{msg.content}</div>
                          ) : (
                            <div className="prose prose-sm prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800">
                              <ReactMarkdown
                                components={{
                                  p: ({node, ...props}) => <p className="mb-4 last:mb-0 text-[13px] text-slate-300" {...props} />,
                                  ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-4 text-[13px] text-slate-300 space-y-1.5 marker:text-teal-500" {...props} />,
                                  ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-4 text-[13px] text-slate-300 space-y-1.5 marker:text-teal-500" {...props} />,
                                  strong: ({node, ...props}) => <strong className="font-bold text-slate-100" {...props} />,
                                  code: ({node, ...props}) => <code className="bg-slate-950 border border-slate-800 px-1.5 py-0.5 rounded text-teal-300 font-mono text-[11px]" {...props} />
                                }}
                              >
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {messages.length === 1 && !isLoading && (
                  <div className="flex w-full justify-start pl-[4.5rem]">
                    <div className="flex gap-3 flex-wrap max-w-2xl">
                      <button onClick={() => handleQuickAction("Run an Entity Risk Analysis")} className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/50 border border-slate-800 hover:border-teal-500/50 hover:bg-slate-800 transition-all rounded-xl text-xs text-slate-400 hover:text-teal-300 hover:shadow-[0_0_10px_rgba(45,212,191,0.1)]">
                        <ShieldWarning size={16} /> Entity Risk Analysis
                      </button>
                      <button onClick={() => handleQuickAction("Check for Suspicious Patterns")} className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/50 border border-slate-800 hover:border-teal-500/50 hover:bg-slate-800 transition-all rounded-xl text-xs text-slate-400 hover:text-teal-300 hover:shadow-[0_0_10px_rgba(45,212,191,0.1)]">
                        <MagnifyingGlass size={16} /> Suspicious Pattern Check
                      </button>
                      <button onClick={() => handleQuickAction("Cross-Reference Data")} className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/50 border border-slate-800 hover:border-teal-500/50 hover:bg-slate-800 transition-all rounded-xl text-xs text-slate-400 hover:text-teal-300 hover:shadow-[0_0_10px_rgba(45,212,191,0.1)]">
                        <Link size={16} /> Cross-Reference Data
                      </button>
                      <button onClick={() => handleQuickAction("Generate a detailed report")} className="flex items-center gap-2 px-4 py-2.5 bg-slate-900/50 border border-slate-800 hover:border-teal-500/50 hover:bg-slate-800 transition-all rounded-xl text-xs text-slate-400 hover:text-teal-300 hover:shadow-[0_0_10px_rgba(45,212,191,0.1)]">
                        <FileText size={16} /> Generate Report
                      </button>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <div className="p-6 bg-slate-950/90 backdrop-blur-md border-t border-slate-800 flex flex-col gap-3 z-10 shadow-[0_-10px_40px_rgba(0,0,0,0.2)]">
                <form onSubmit={sendMessage} className="relative flex items-center bg-slate-900/50 border border-slate-700/50 rounded-2xl overflow-hidden focus-within:border-teal-500/50 focus-within:ring-1 focus-within:ring-teal-500/30 transition-all shadow-inner">
                  <div className="pl-5 text-slate-500">
                    <ChatCircleDots size={22} weight="fill" />
                  </div>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Enter your query or command..."
                    className="w-full bg-transparent text-slate-200 px-4 py-4 focus:outline-none font-sans placeholder:text-slate-600 text-[13px]"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="absolute right-2 bg-slate-800/80 hover:bg-teal-600 disabled:bg-slate-900/50 disabled:text-slate-700 text-teal-400 hover:text-white px-5 py-2.5 rounded-xl font-bold uppercase tracking-widest text-[10px] transition-all flex items-center gap-2 border border-slate-700/50 hover:border-teal-500 disabled:border-transparent hover:shadow-[0_0_15px_rgba(20,184,166,0.4)]"
                  >
                    {isLoading ? <CircleNotch size={16} className="animate-spin" /> : <PaperPlaneTilt size={16} weight="fill" />}
                    Transmit
                  </button>
                </form>
                <div className="flex items-center justify-center gap-4 text-[9px] font-mono text-slate-600 tracking-widest uppercase mt-1">
                  <span className="flex items-center gap-1.5"><LockKey size={12}/> Secure Enclave</span>
                  <span className="text-slate-800">•</span>
                  <span className="flex items-center gap-1.5"><ShieldCheck size={12}/> End-To-End Encryption</span>
                  <span className="text-slate-800">•</span>
                  <span className="flex items-center gap-1.5"><ShieldWarning size={12}/> Audit Log Enabled</span>
                </div>
              </div>
            </>
          )}

          {activeTab === 'history' && (
            <div className="flex-1 flex flex-col p-8 overflow-y-auto">
              <div className="flex items-center gap-3 mb-8 border-b border-slate-800 pb-4">
                <Clock size={32} className="text-teal-500" />
                <h3 className="text-2xl font-black text-white tracking-widest uppercase">Conversation History</h3>
              </div>
              
              <div className="flex flex-col gap-4">
                {[
                  { id: 'CZ-83921', title: 'Suspicious Offshore Transfers', date: 'Today, 14:32', preview: 'Analyzed 14 offshore transactions linked to shell accounts in Panama.' },
                  { id: 'NEXUS-CO', title: 'Entity Risk Check - Nexus Corp', date: 'Yesterday, 09:15', preview: 'Cross-referenced directors with known high-risk individuals on the watch list.' },
                  { id: 'PTN-009', title: 'Tax Evasion Pattern Analysis', date: 'Aug 25, 2026', preview: 'Identified circular fund movement across 3 local businesses.' },
                  { id: 'CZ-11204', title: 'Asset Declaration Discrepancy', date: 'Aug 21, 2026', preview: 'Flagged a $2.4M real estate purchase not matching declared income.' }
                ].map((chat, i) => (
                  <div key={i} className="bg-slate-900/50 border border-slate-800 hover:border-teal-500/50 rounded-xl p-5 transition-all group flex justify-between items-center cursor-pointer"
                    onClick={() => {
                      setCitizenId(chat.id);
                      setMessages([
                        { role: 'user', content: `Load history for: ${chat.title}` },
                        { role: 'assistant', content: `Retrieving secure archives for **${chat.id}**...\n\n> ${chat.preview}\n\n*Historical context loaded. You may resume the investigation.*` }
                      ]);
                      setActiveTab('chat');
                    }}
                  >
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-3">
                        <h4 className="text-slate-200 font-bold text-base group-hover:text-teal-400 transition-colors">{chat.title}</h4>
                        <span className="bg-slate-800 text-slate-400 px-2 py-0.5 rounded text-[10px] font-mono tracking-widest border border-slate-700">{chat.id}</span>
                      </div>
                      <p className="text-slate-400 text-sm max-w-2xl">{chat.preview}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className="text-slate-500 font-mono text-[10px]">{chat.date}</span>
                      <button className="text-teal-500 text-xs font-bold uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                        Resume Session &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
