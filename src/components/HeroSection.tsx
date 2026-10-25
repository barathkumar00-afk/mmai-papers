import React from 'react';
import { BrainHeroCanvas } from './BrainHeroCanvas';

interface HeroSectionProps {
  onStartAnalysis: () => void;
  onExploreArchitecture: () => void;
  onExploreEvidence: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onStartAnalysis,
  onExploreArchitecture,
  onExploreEvidence
}) => {
  return (
    <section id="platform" className="relative z-10 w-full min-h-[920px] flex flex-col justify-center pt-24 pb-16">
      <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Column: Clinical Title & Grounding */}
        <div className="lg:col-span-6 flex flex-col items-start gap-4 z-10">
          {/* Technical protocol badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#080e1a]/80 border border-[#00f2fe]/30 backdrop-blur-md shadow-[0_0_20px_rgba(0,242,254,0.15)]">
            <span className="inline-block w-2 h-2 rounded-full bg-[#00f2fe] animate-ping" />
            <span className="font-mono text-[11px] text-[#e0fdff] tracking-widest uppercase font-semibold">
              MULTIMODAL CLINICAL INTELLIGENCE // RESEARCH PROTOCOL v2.4
            </span>
          </div>

          {/* Cinematic Title */}
          <h1 className="font-headline text-3xl sm:text-4xl lg:text-[3.25rem] lg:leading-[3.75rem] text-[#dde2f3] font-bold tracking-tight">
            Understand.{' '}
            <span className="bg-gradient-to-r from-[#00f2fe] via-[#b4c5ff] to-[#e2d4ff] bg-clip-text text-transparent">
              Explain.
            </span>{' '}
            Support Clinical Decisions.
          </h1>

          {/* Abstract */}
          <p className="font-body text-base lg:text-lg text-[#b9cacb] max-w-xl leading-relaxed">
            An evidence-grounded multimodal AI framework synthesizing medical imaging, phonetics, clinical biomarkers, and retrieval-augmented reasoning into fully traceable diagnostic justifications.
          </p>

          {/* Live Metric Badges */}
          <div className="grid grid-cols-3 gap-3 w-full max-w-xl my-2">
            <div className="p-3 rounded-xl bg-[#080e1a]/70 border border-[#3a494b]/30 backdrop-blur-md">
              <span className="block font-mono text-[10px] text-[#849495] uppercase tracking-wider">MODALITIES</span>
              <span className="font-mono text-xs sm:text-sm text-[#e0fdff] font-semibold">3 (IMG+AUD+EHR)</span>
            </div>
            <div className="p-3 rounded-xl bg-[#080e1a]/70 border border-[#3a494b]/30 backdrop-blur-md">
              <span className="block font-mono text-[10px] text-[#849495] uppercase tracking-wider">ALIGNMENT</span>
              <span className="font-mono text-xs sm:text-sm text-[#00f2fe] font-semibold">98.4% ATTN</span>
            </div>
            <div className="p-3 rounded-xl bg-[#080e1a]/70 border border-[#3a494b]/30 backdrop-blur-md">
              <span className="block font-mono text-[10px] text-[#849495] uppercase tracking-wider">TRACEABILITY</span>
              <span className="font-mono text-xs sm:text-sm text-emerald-400 font-semibold">100% AUDITABLE</span>
            </div>
          </div>

          {/* Dual CTA Buttons */}
          <div className="flex flex-wrap items-center gap-4 mt-2">
            <button
              onClick={onStartAnalysis}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-[#00f2fe] to-[#0053db] text-[#080e1a] font-headline text-sm font-bold tracking-wide shadow-[0_0_24px_rgba(0,242,254,0.35)] hover:shadow-[0_0_36px_rgba(0,242,254,0.55)] transition-all flex items-center gap-2 group cursor-pointer active:scale-95"
            >
              <span className="material-symbols-outlined text-[20px] group-hover:rotate-45 transition-transform">
                biotech
              </span>
              Start Case Analysis
            </button>

            <button
              onClick={onExploreArchitecture}
              className="px-5 py-3 rounded-xl bg-[#080e1a]/80 border border-[#00f2fe]/30 text-[#e0fdff] font-body text-sm font-medium hover:border-[#00f2fe] hover:bg-[#161c28] transition-all flex items-center gap-2 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">account_tree</span>
              Explore Architecture
            </button>

            <button
              onClick={onExploreEvidence}
              className="px-3 py-2 text-[#b9cacb] hover:text-[#00f2fe] font-mono text-xs uppercase tracking-wider flex items-center gap-1 transition-colors cursor-pointer"
            >
              PubMed Grounding →
            </button>
          </div>

          <div className="flex items-center gap-2 text-[#849495] font-mono text-xs pt-1">
            <span className="material-symbols-outlined text-[15px] text-[#00f2fe]">info</span>
            <span>AI-assisted clinical decision support — research prototype, not an autonomous diagnostic device.</span>
          </div>
        </div>

        {/* Right Column: 3D Scene Viewport + Floating Telemetry HUD */}
        <div className="lg:col-span-6 relative flex items-center justify-center min-h-[580px] lg:min-h-[660px]">
          {/* 3D Scene Wrapper with Surgical HUD corners */}
          <div className="relative w-full h-[620px] rounded-2xl bg-[#080e1a]/40 border border-[#00f2fe]/20 shadow-[0_0_50px_rgba(0,242,254,0.1)] overflow-hidden">
            {/* Corner HUD Reticles */}
            <div className="absolute top-3 left-3 z-20 flex items-center gap-2 font-mono text-xs text-[#e0fdff]/70">
              <span className="w-2 h-2 border-t-2 border-l-2 border-[#00f2fe] inline-block"></span>
              <span>VOLUMETRIC NEURAL MANIFOLD // v2.4</span>
            </div>
            <div className="absolute top-3 right-3 z-20 font-mono text-xs text-[#e0fdff]/70">
              <span>RES: 1024³ // Z-SLICE: 088</span>
              <span className="w-2 h-2 border-t-2 border-r-2 border-[#00f2fe] inline-block ml-1"></span>
            </div>
            <div className="absolute bottom-3 left-3 z-20 flex items-center gap-2 font-mono text-xs text-[#849495]">
              <span className="w-2 h-2 border-b-2 border-l-2 border-[#00f2fe] inline-block"></span>
              <span>ROT_VEC: [0.441, -0.198, 0.875]</span>
            </div>
            <div className="absolute bottom-3 right-3 z-20 font-mono text-xs text-emerald-400">
              <span>SYNAPSE STREAM: ACTIVE</span>
              <span className="w-2 h-2 border-b-2 border-r-2 border-emerald-400 inline-block ml-1"></span>
            </div>

            {/* THREE.JS BRAIN & SYNAPSE NETWORK */}
            <BrainHeroCanvas />

            {/* Floating Glassmorphic Modality Telemetry Cards */}
            {/* Modality 1: Image */}
            <div className="absolute top-12 left-4 z-20 max-w-[210px] p-3 rounded-xl bg-[#080e1a]/85 border border-[#00f2fe]/40 backdrop-blur-md shadow-[0_8px_32px_rgba(0,242,254,0.15)] hover:border-[#00f2fe] transition-all cursor-pointer">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-[#3a494b]/30">
                <span className="font-mono text-[10px] font-bold text-[#00f2fe] uppercase">[ IMAGE ] DICOM / CXR</span>
                <span className="text-[10px] font-mono text-emerald-400">99.1% CONF</span>
              </div>
              <p className="font-mono text-[11px] text-[#b9cacb]">Dual-lobe opacities segment: S4/S8</p>
              <div className="w-full h-1 bg-[#1a202c] mt-1.5 rounded-full overflow-hidden">
                <div className="h-full bg-[#00f2fe] w-[89%]"></div>
              </div>
            </div>

            {/* Modality 2: Patient Speech */}
            <div className="absolute top-1/4 -right-2 z-20 max-w-[220px] p-3 rounded-xl bg-[#080e1a]/85 border border-[#e2d4ff]/30 backdrop-blur-md shadow-xl hover:border-[#d0bcff] transition-all">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-[#3a494b]/30">
                <span className="font-mono text-[10px] font-bold text-[#d0bcff] uppercase">[ AUDIO ] SPEECH PHONETICS</span>
                <span className="w-2 h-2 rounded-full bg-[#d0bcff] animate-ping"></span>
              </div>
              <p className="font-mono text-[11px] text-[#b9cacb]">Acoustic Dyspnea / Stridor detected (440Hz peak)</p>
              {/* Mini visualizer waveform */}
              <div className="flex items-end gap-1 h-4 mt-2">
                <span className="w-1 bg-[#d0bcff] h-2 animate-pulse"></span>
                <span className="w-1 bg-[#d0bcff] h-4"></span>
                <span className="w-1 bg-[#d0bcff] h-3 animate-pulse"></span>
                <span className="w-1 bg-[#d0bcff] h-1"></span>
                <span className="w-1 bg-[#d0bcff] h-4 animate-pulse"></span>
                <span className="w-1 bg-[#d0bcff] h-2"></span>
              </div>
            </div>

            {/* Modality 3: EHR / Clinical Labs */}
            <div className="absolute bottom-20 left-6 z-20 max-w-[230px] p-3 rounded-xl bg-[#080e1a]/85 border border-[#b4c5ff]/40 backdrop-blur-md shadow-xl hover:border-[#00f2fe] transition-all">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-[#3a494b]/30">
                <span className="font-mono text-[10px] font-bold text-[#b4c5ff] uppercase">[ EHR ] CLINICAL LABS</span>
                <span className="text-[10px] font-mono text-[#ffb4ab] font-bold">CRITICAL</span>
              </div>
              <div className="font-mono text-[11px] text-[#dde2f3] flex flex-col gap-0.5">
                <span>SpO2: <span className="text-[#ffb4ab] font-semibold">88% (Room Air)</span></span>
                <span>Troponin-I: <span className="text-emerald-400">0.02 ng/mL (Neg)</span></span>
                <span>CRP: <span className="text-[#ffb4ab]">42 mg/L (Elevated)</span></span>
              </div>
            </div>

            {/* Modality 4: Grounded RAG Satellite */}
            <div className="absolute bottom-16 right-4 z-20 max-w-[220px] p-3 rounded-xl bg-[#080e1a]/85 border border-emerald-400/30 backdrop-blur-md shadow-xl hover:border-emerald-400 transition-all">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-[#3a494b]/30">
                <span className="font-mono text-[10px] font-bold text-emerald-400 uppercase">[ RAG ] EVIDENCE ANCHOR</span>
                <span className="font-mono text-[10px] text-[#849495]">PMID: 3829104</span>
              </div>
              <p className="font-mono text-[11px] text-[#b9cacb] truncate">ATS 2024 Guidelines: Acute Hypoxemic Respiratory</p>
            </div>

            {/* Central Crosshair Projection Rings */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="w-72 h-72 rounded-full border border-[#00f2fe]/10 animate-[spin_24s_linear_infinite]"></div>
              <div className="w-96 h-96 rounded-full border border-dashed border-[#b4c5ff]/15 animate-[spin_40s_linear_infinite_reverse]"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Pulsating Scroll Guide */}
      <div className="flex flex-col items-center justify-center mt-12 gap-2 text-[#849495]">
        <span className="font-mono text-[10px] tracking-widest uppercase">SCROLL TO EXPLORE ARCHITECTURE</span>
        <div className="w-0.5 h-10 bg-gradient-to-b from-[#00f2fe] to-transparent animate-pulse"></div>
      </div>
    </section>
  );
};
