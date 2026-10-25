import React, { useState } from 'react';

interface ReportSectionProps {
  onOpenPdfModal: () => void;
  onOpenTraceModal: () => void;
}

export const ReportSection: React.FC<ReportSectionProps> = ({
  onOpenPdfModal,
  onOpenTraceModal
}) => {
  const [isSigned, setIsSigned] = useState(true);

  return (
    <section id="clinical-report" className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold">
          EXPORTABLE CLINICAL SPECIFICATION
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          The Grounded Clinical Dossier
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          A structured, cryptographic clinical document binding all input telemetry, cross-attention vectors, and medical literature citations.
        </p>
      </div>

      {/* Isometric Glass Document Card */}
      <div className="w-full max-w-4xl mx-auto p-6 md:p-10 rounded-3xl bg-[#080e1a]/90 border border-[#00f2fe]/30 backdrop-blur-2xl shadow-[0_20px_60px_rgba(0,0,0,0.7)] relative overflow-hidden">
        {/* Top Report Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#3a494b]/30 gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[#00f2fe] text-[24px]">description</span>
              <h4 className="font-headline text-base sm:text-lg text-[#dde2f3] font-bold">
                CLINICAL MULTIMODAL AUDIT DOSSIER
              </h4>
            </div>
            <span className="font-mono text-xs text-[#849495]">
              PROTOCOL: NEURO-AI-R24 // HASH: 0x9f82...3b1a
            </span>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs">
            <span className="px-2.5 py-1 rounded bg-[#1a202c] text-[#849495] border border-[#3a494b]/30">
              STATUS: PEER_REVIEW
            </span>
            <span className="px-2.5 py-1 rounded bg-emerald-400/10 text-emerald-400 border border-emerald-400/30 font-semibold">
              FAISS VERIFIED
            </span>
          </div>
        </div>

        {/* Report Body Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="space-y-2 font-body text-xs">
            <span className="font-mono text-xs text-[#849495] block uppercase font-semibold">
              PATIENT PROFILE &amp; ACQUISITION
            </span>
            <div className="p-4 rounded-xl bg-[#161c28] font-mono text-xs text-[#b9cacb] space-y-1.5 border border-[#3a494b]/30">
              <div className="flex justify-between">
                <span>AGE / GENDER:</span>
                <span className="text-[#dde2f3] font-semibold">58 / M</span>
              </div>
              <div className="flex justify-between">
                <span>INTAKE TIMESTAMP:</span>
                <span className="text-[#dde2f3]">2025-05-14T08:24:19Z</span>
              </div>
              <div className="flex justify-between">
                <span>PRIMARY SCAN:</span>
                <span className="text-[#00f2fe]">3T Brain MRI (Axial T1+Gd / FLAIR)</span>
              </div>
              <div className="flex justify-between">
                <span>AUDIO DURATION:</span>
                <span className="text-[#d0bcff]">14.2s (Cognitive Speech Acoustic)</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 font-body text-xs">
            <span className="font-mono text-xs text-[#849495] block uppercase font-semibold">
              UNCERTAINTY QUANTIFICATION
            </span>
            <div className="p-4 rounded-xl bg-[#161c28] font-mono text-xs text-[#b9cacb] space-y-1.5 border border-[#3a494b]/30">
              <div className="flex justify-between">
                <span>EPISTEMIC UNCERTAINTY:</span>
                <span className="text-[#00f2fe] font-semibold">6.4%</span>
              </div>
              <div className="flex justify-between">
                <span>ALEATORIC (DATA NOISE):</span>
                <span className="text-[#b4c5ff] font-semibold">4.2%</span>
              </div>
              <div className="flex justify-between font-bold text-[#dde2f3] pt-1 border-t border-[#3a494b]/30">
                <span>TOTAL MODEL ENTROPY:</span>
                <span className="text-emerald-400">10.6% (Low Risk)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Attending Signature & Review Notice */}
        <div className="p-4 rounded-xl bg-[#161c28] border border-[#3a494b]/30 flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <span className="font-mono text-xs text-[#00f2fe] uppercase block font-semibold">
              ATTENDING PHYSICIAN GATING
            </span>
            <p className="font-body text-xs text-[#b9cacb] mt-0.5">
              Signature affirms diagnostic validation of AI observations prior to therapeutic actions.
            </p>
          </div>

          <button
            onClick={() => setIsSigned(!isSigned)}
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#242a36] transition-colors cursor-pointer text-left"
            title="Click to toggle signature verification"
          >
            <div
              className={`h-10 w-44 border-b flex items-end justify-center font-mono text-xs italic pb-1 ${
                isSigned
                  ? 'border-[#00f2fe] text-[#00f2fe]'
                  : 'border-[#849495] text-[#849495] line-through'
              }`}
            >
              {isSigned ? 'Dr. Sarah Chen, MD' : '[ Unsigned ]'}
            </div>
            <span className={`material-symbols-outlined ${isSigned ? 'text-emerald-400' : 'text-[#849495]'}`}>
              {isSigned ? 'draw' : 'edit'}
            </span>
          </button>
        </div>

        {/* Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-[#3a494b]/20">
          <div className="flex items-center gap-3">
            <button
              onClick={onOpenPdfModal}
              className="px-4 py-2.5 rounded-lg bg-[#00f2fe] text-[#080e1a] font-headline text-xs font-semibold flex items-center gap-2 hover:opacity-90 transition-all cursor-pointer shadow-[0_0_15px_rgba(0,242,254,0.3)] active:scale-95"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              Export Clinical PDF
            </button>

            <button
              onClick={onOpenTraceModal}
              className="px-4 py-2.5 rounded-lg bg-[#1a202c] hover:bg-[#242a36] font-headline text-xs text-[#dde2f3] border border-[#3a494b]/30 flex items-center gap-2 transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">visibility</span>
              View Interactive Trace
            </button>
          </div>

          <span className="font-mono text-xs text-[#849495]">SECURE SHA-256 CLINICAL RECORD</span>
        </div>
      </div>
    </section>
  );
};
