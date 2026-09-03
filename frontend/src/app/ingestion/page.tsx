"use client";

import { UploadSimple, Play, FileCsv, CheckCircle } from "@phosphor-icons/react";
import useSWR from "swr";
import { useState, useRef, useEffect } from "react";

const API = "http://127.0.0.1:8000";
const fetcher = (url: string) => fetch(url).then(r => r.json());

interface Dataset {
  name: string;
  domain: string;
  size_kb: number;
  status: string;
}

export default function IngestionHub() {
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (running) {
      timer = setInterval(() => setElapsedSeconds(s => s + 1), 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(timer);
  }, [running]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const progressPct = Math.min(99, (elapsedSeconds / 420) * 100);

  const { data: datasetsData, mutate } = useSWR<{ datasets: Dataset[] }>(
    `${API}/api/v1/system/datasets`,
    fetcher
  );
  const datasets = datasetsData?.datasets || [];

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const res = await fetch(`${API}/api/v1/system/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadResult(`Successfully uploaded ${files.length} datasets. Ready to reload engine!`);
        mutate();
      } else {
        setUploadResult(`Upload failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      setUploadResult("Error: Could not connect to backend to upload files.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleRunPipeline = async () => {
    setRunning(true);
    setPipelineResult("Initializing pipeline...");
    try {
      const res = await fetch(`${API}/api/v1/system/run-pipeline`, { method: "POST" });
      if (!res.ok) {
        setPipelineResult("Failed to start pipeline.");
        setRunning(false);
        return;
      }
      
      // Start polling the status
      const interval = setInterval(async () => {
        try {
          const statRes = await fetch(`${API}/api/v1/system/pipeline-status`);
          const statData = await statRes.json();
          
          if (statData.status === "running") {
            setPipelineResult(statData.message || "Processing data... please wait (~2 mins).");
          } else if (statData.status === "completed") {
            clearInterval(interval);
            setRunning(false);
            setPipelineResult(statData.message || "Pipeline completed successfully!");
            mutate(); // refresh datasets
          } else if (statData.status === "error") {
            clearInterval(interval);
            setRunning(false);
            setPipelineResult(statData.message || "Pipeline encountered an error.");
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);
      
    } catch (err) {
      setPipelineResult("Error: Could not connect to backend to execute pipeline.");
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <header className="flex flex-col gap-1 pb-4 border-b-2 border-blue-700/20">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 uppercase">Data Ingestion Hub</h1>
        <p className="text-sm text-slate-500">Securely upload and process organization datasets through the Graph AI Intelligence Pipeline.</p>
      </header>

      <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 text-sm">
        <strong>Tip:</strong> Ensure your CSV files have standard column names (like cnic, declared_income, property_value). The system automatically handles empty or missing columns.
      </div>

       <section className="gov-panel flex flex-col">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">File Upload Terminal</div>
        <div className="p-8 flex flex-col items-center justify-center border-2 border-dashed border-slate-300 m-4 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => !uploading && fileRef.current?.click()}>
          <UploadSimple size={32} className={`mb-2 ${uploading ? 'animate-bounce text-teal-500' : 'text-slate-400'}`} />
          <span className="text-sm font-medium text-slate-700">
            {uploading ? "Uploading Datasets..." : "Select Datasets (CSV or XLSX)"}
          </span>
          <span className="text-xs text-slate-500 mt-1">Files are stored locally and never sent to external servers.</span>
          <input ref={fileRef} type="file" accept=".csv,.xlsx" multiple className="hidden" onChange={handleFileChange} />
        </div>
        {uploadResult && (
          <div className={`mx-4 mb-4 p-3 text-xs font-mono border ${uploadResult.startsWith('Error') || uploadResult.startsWith('Upload failed') ? 'bg-red-50 text-red-700 border-red-200' : 'bg-teal-50 text-teal-700 border-teal-200'}`}>
            {uploadResult}
          </div>
        )}
      </section>

      <section className="gov-panel flex flex-col">
        <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-slate-900">Available Datasets</div>
        {datasets.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500 font-mono">
            No datasets uploaded yet. Use the upload terminal above.
          </div>
        ) : (
          <ul className="divide-y divide-slate-200">
            {datasets.map((d) => (
              <DatasetRow key={d.name} name={d.name} domain={`${d.domain} (${d.size_kb} KB)`} status={d.status} />
            ))}
          </ul>
        )}
      </section>

      {pipelineResult && (
        <div className={`p-3 text-sm font-mono ${pipelineResult.startsWith('Error') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-green-50 text-green-700 border border-green-200'}`}>
          {pipelineResult}
        </div>
      )}

      <div className="flex justify-end pt-4">
        <button onClick={handleRunPipeline} disabled={running} className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-semibold py-3 px-8 rounded-sm shadow-sm flex items-center gap-2 transition-colors uppercase text-sm tracking-wider">
          <Play weight="fill" />
          {running ? "Running..." : "Reload Intelligence Engine"}
        </button>
      </div>
    </div>
  );
}

function DatasetRow({ name, domain, status }: { name: string; domain: string; status: string }) {
  return (
    <li className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors">
      <div className="flex items-center gap-3">
        <FileCsv size={24} className="text-slate-400" />
        <div className="flex flex-col">
          <span className="text-sm font-medium text-slate-900 font-mono">{name}</span>
          <span className="text-xs text-slate-500">{domain}</span>
        </div>
      </div>
      <div className="flex items-center gap-1 text-green-700 text-xs font-semibold bg-green-50 px-2 py-1 border border-green-200 rounded-sm uppercase">
        <CheckCircle weight="fill" />
        {status}
      </div>
    </li>
  );
}
