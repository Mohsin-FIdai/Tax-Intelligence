"use client";

import { useState, useRef } from "react";
import { FilePdf, SpinnerGap } from "@phosphor-icons/react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

export default function GenerateNoticeButton({ citizen }: { citizen: any }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const noticeRef = useRef<HTMLDivElement>(null);

  if (!["C", "D", "E"].includes(citizen.risk_category)) {
    return null;
  }

  const handleGenerate = async () => {
    if (!noticeRef.current) return;
    setIsGenerating(true);

    try {
      const canvas = await html2canvas(noticeRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
      pdf.save(`Legal_Notice_${citizen.cnic || citizen.citizen_id}.pdf`);
    } catch (error) {
      console.error("Error generating PDF", error);
      alert("Failed to generate PDF. Check console for details.");
    } finally {
      setIsGenerating(false);
    }
  };

  const today = new Date().toLocaleDateString("en-PK", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <>
      <button
        onClick={handleGenerate}
        disabled={isGenerating}
        className="flex items-center gap-2 bg-red-700 hover:bg-red-800 text-white px-4 py-2 rounded text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-70 shadow-sm"
      >
        {isGenerating ? <SpinnerGap className="animate-spin" size={16} /> : <FilePdf size={16} />}
        {isGenerating ? "Generating PDF..." : "Generate Legal Notice"}
      </button>

      {/* Off-screen PDF Template */}
      <div className="absolute top-[-9999px] left-[-9999px] z-[-1] overflow-hidden">
        <div
          ref={noticeRef}
          className="p-12 w-[800px] h-[1131px]"
          style={{ 
            fontFamily: "'Times New Roman', Times, serif",
            backgroundColor: "#ffffff",
            color: "#000000"
          }}
        >
          {/* Header */}
          <div className="flex flex-col items-center pb-6 mb-8 mt-4" style={{ borderBottom: "2px solid #000000" }}>
            <img src="/notice-logo.png" alt="FTI Logo" className="h-28 mb-4 object-contain" />
            <h1 className="text-3xl font-bold uppercase tracking-widest text-center" style={{ letterSpacing: '0.2em' }}>
              Federal Tax Intelligence
            </h1>
            <p className="text-sm tracking-widest mt-1 uppercase font-bold" style={{ color: "#374151" }}>Government of Pakistan</p>
          </div>

          <h2 className="text-xl font-bold text-center underline mb-8 tracking-wider">LEGAL NOTICE</h2>

          <div className="mb-8 space-y-2 text-[15px] font-bold">
            <p><span className="w-32 inline-block">Subject:</span> Notice Regarding Potential Undeclared Assets and Discrepancies in Reported Wealth</p>
            <div className="mt-6 flex flex-col gap-1">
              <p><span className="w-32 inline-block">To:</span> {citizen.canonical_name || citizen.name || "N/A"}</p>
              <p><span className="w-32 inline-block">CNIC:</span> {citizen.cnic ? String(citizen.cnic).replace(/\.0$/, "") : "N/A"}</p>
              <p><span className="w-32 inline-block flex-shrink-0 float-left">Address:</span> <span className="block ml-32">{citizen.address || "N/A"}{citizen.city ? `, ${citizen.city}` : ""}{citizen.province ? `, ${citizen.province}` : ""}</span></p>
              <div className="clear-both"></div>
              <p><span className="w-32 inline-block">Date:</span> {today}</p>
              <p><span className="w-32 inline-block">Reference No.:</span> FTI-LN-{String(citizen.citizen_id).substring(0,8).toUpperCase()}-{new Date().getFullYear()}</p>
            </div>
          </div>

          <div className="space-y-5 text-justify text-[15px] leading-relaxed">
            <p>Dear {citizen.canonical_name || citizen.name || "Taxpayer"},</p>
            
            <p>
              It has come to the attention of the competent tax authority that certain discrepancies may exist between the assets, financial transactions, and sources of income reported by you and information available to the authority through relevant records and financial data.
            </p>

            <p>
              The preliminary information indicates potential undeclared assets and/or income that may require clarification. These observations may include discrepancies involving property holdings, bank transactions, business interests, investments, or other financial activities.
            </p>

            <p>
              You are hereby required to provide, within <strong>14 days</strong> of receipt of this notice, a written explanation and supporting documentation concerning the identified discrepancies, including:
            </p>

            <ol className="list-decimal pl-8 space-y-2 my-4">
              <li>Details and source of funds for the assets identified;</li>
              <li>Evidence of declared income corresponding to the identified assets;</li>
              <li>Relevant bank statements, property documents, business records, and other supporting documentation;</li>
              <li>Details of any assets or income that may have been omitted from previous declarations; and</li>
              <li>Any other information necessary to establish the lawful source and tax treatment of the identified wealth.</li>
            </ol>

            <p>
              Failure to provide a satisfactory explanation or supporting documentation within the prescribed period may result in further proceedings under the applicable tax laws and regulations.
            </p>

            <p>
              This notice is issued for the purpose of seeking clarification and does not, by itself, constitute a final determination that any undeclared income, tax liability, or unlawful conduct has occurred.
            </p>

            <p>
              You are advised to ensure that all information submitted in response to this notice is complete, accurate, and supported by appropriate documentary evidence.
            </p>

            <div className="pt-8 mt-12 flex justify-between items-end" style={{ borderTop: "1px solid #d1d5db" }}>
              <div>
                <p className="mb-12">Sincerely,</p>
                <p className="font-bold text-lg">Mohsin Fidai</p>
                <p className="italic" style={{ color: "#374151" }}>Head of Department</p>
                <p className="font-bold">Federal Tax Intelligence</p>
              </div>
              <div className="text-sm font-bold text-right" style={{ color: "#4b5563" }}>
                <p>Contact: 051-111-222-333</p>
                <p>Email: legal@fti.gov.pk</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
