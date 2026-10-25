import React, { useState } from 'react';

export const FragmentedSection: React.FC = () => {
  const [isConverged, setIsConverged] = useState(false);

  return (
    <section className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold">
          THE CLINICAL CHALLENGE
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          Clinical Information Is Fragmented.
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          Different modalities contain isolated fragments of the patient story. When analyzed in silos, critical diagnostic signals are lost in translation.
        </p>
      </div>

      {/* 3 Large Interactive Modality Cards with Convergence State */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 transition-all duration-700">
        {/* Panel 1: Medical Imaging */}
        <div
          className={`p-6 rounded-2xl bg-[#161c28]/70 border transition-all duration-500 backdrop-blur-lg flex flex-col justify-between ${
            isConverged
              ? 'border-[#00f2fe] shadow-[0_0_35px_rgba(0,242,254,0.3)] scale-[1.02]'
              : 'border-[#00f2fe]/20 hover:border-[#00f2fe]/50 hover:shadow-[0_0_30px_rgba(0,242,254,0.15)]'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="p-2 rounded-lg bg-[#00f2fe]/10 text-[#00f2fe] material-symbols-outlined">
                radiology
              </span>
              <span className="font-mono text-xs text-[#849495]">MODALITY // 01</span>
            </div>
            <h3 className="font-headline text-lg text-[#dde2f3] font-semibold mb-1">
              Visual Evidence
            </h3>
            <p className="font-body text-sm text-[#b9cacb] mb-4">
              DICOM chest radiographs and CT reconstructions provide spatial topography, tissue densities, and lesion volumes, but lack temporal onset or physiological decline velocity.
            </p>
            <div className="p-3 rounded-lg bg-[#080e1a]/80 border border-[#3a494b]/30 font-mono text-xs space-y-1">
              <div className="text-[#6ff6ff]">RAD_FINDING: Peripheral GGOs</div>
              <div className="text-[#849495]">DISTRIBUTION: Bilateral Base (Dice 0.91)</div>
              <div className="text-[#849495]">ACQUISITION: PA Upright CXR</div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#3a494b]/20 flex items-center justify-between text-[#849495] font-mono text-xs">
            <span>SPATIAL CONTEXT</span>
            <span className={isConverged ? 'text-emerald-400 font-bold' : 'text-[#00f2fe]'}>
              {isConverged ? 'FUSED TO CORE' : 'ISOLATED'}
            </span>
          </div>
        </div>

        {/* Panel 2: Patient Speech */}
        <div
          className={`p-6 rounded-2xl bg-[#161c28]/70 border transition-all duration-500 backdrop-blur-lg flex flex-col justify-between ${
            isConverged
              ? 'border-[#d0bcff] shadow-[0_0_35px_rgba(208,188,255,0.3)] scale-[1.02]'
              : 'border-[#e2d4ff]/20 hover:border-[#e2d4ff]/50 hover:shadow-[0_0_30px_rgba(226,212,255,0.15)]'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="p-2 rounded-lg bg-[#e2d4ff]/10 text-[#d0bcff] material-symbols-outlined">
                record_voice_over
              </span>
              <span className="font-mono text-xs text-[#849495]">MODALITY // 02</span>
            </div>
            <h3 className="font-headline text-lg text-[#dde2f3] font-semibold mb-1">
              Acoustic &amp; Symptom Nuance
            </h3>
            <p className="font-body text-sm text-[#b9cacb] mb-4">
              Vocal acoustics capture respiratory strain, speech pauses per syllable, and subtle dyspnea indices that electronic medical charts rarely record systematically.
            </p>
            <div className="p-3 rounded-lg bg-[#080e1a]/80 border border-[#3a494b]/30 font-mono text-xs space-y-1">
              <div className="text-[#d0bcff]">PHONETICS: Stridor / Sub-glottic Wheeze</div>
              <div className="text-[#849495]">RESP_BURST_RATE: 28 / min</div>
              <div className="text-[#849495]">VOICE_JITTER: 3.2% (Elevated Fatigue)</div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#3a494b]/20 flex items-center justify-between text-[#849495] font-mono text-xs">
            <span>ACOUSTIC DYNAMICS</span>
            <span className={isConverged ? 'text-emerald-400 font-bold' : 'text-[#d0bcff]'}>
              {isConverged ? 'FUSED TO CORE' : 'ISOLATED'}
            </span>
          </div>
        </div>

        {/* Panel 3: Clinical Lab / Context */}
        <div
          className={`p-6 rounded-2xl bg-[#161c28]/70 border transition-all duration-500 backdrop-blur-lg flex flex-col justify-between ${
            isConverged
              ? 'border-[#b4c5ff] shadow-[0_0_35px_rgba(180,197,255,0.3)] scale-[1.02]'
              : 'border-[#b4c5ff]/20 hover:border-[#b4c5ff]/50 hover:shadow-[0_0_30px_rgba(180,197,255,0.15)]'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="p-2 rounded-lg bg-[#b4c5ff]/10 text-[#b4c5ff] material-symbols-outlined">
                vital_signs
              </span>
              <span className="font-mono text-xs text-[#849495]">MODALITY // 03</span>
            </div>
            <h3 className="font-headline text-lg text-[#dde2f3] font-semibold mb-1">
              Longitudinal Context &amp; Chemistry
            </h3>
            <p className="font-body text-sm text-[#b9cacb] mb-4">
              Serum biochemistry, vital sign trajectories, and past comorbidities provide systemic context, but cannot localize anatomical abnormalities or quantify phonatory effort.
            </p>
            <div className="p-3 rounded-lg bg-[#080e1a]/80 border border-[#3a494b]/30 font-mono text-xs space-y-1">
              <div className="text-[#b4c5ff]">O2_SATURATION: 88% on Room Air</div>
              <div className="text-[#849495]">INFLAMMATION: CRP 42 mg/L</div>
              <div className="text-[#849495]">ONSET: Acute progressive (48 hours)</div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#3a494b]/20 flex items-center justify-between text-[#849495] font-mono text-xs">
            <span>BIOCHEMISTRY LOGS</span>
            <span className={isConverged ? 'text-emerald-400 font-bold' : 'text-[#b4c5ff]'}>
              {isConverged ? 'FUSED TO CORE' : 'ISOLATED'}
            </span>
          </div>
        </div>
      </div>

      {/* Convergence Action Controller */}
      <div className="flex flex-col items-center justify-center mt-8 gap-3">
        <button
          onClick={() => setIsConverged(!isConverged)}
          className={`px-6 py-3 rounded-xl border font-headline text-sm font-medium transition-all shadow-[0_0_20px_rgba(0,242,254,0.15)] flex items-center gap-2 cursor-pointer ${
            isConverged
              ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300'
              : 'bg-[#242a36] border-[#00f2fe]/40 hover:bg-[#2f3542] text-[#e0fdff]'
          }`}
        >
          <span className="material-symbols-outlined text-[#00f2fe]">
            {isConverged ? 'check_circle' : 'join_inner'}
          </span>
          {isConverged ? 'Reset Modality Separation' : 'Simulate Modality Convergence'}
        </button>

        {isConverged && (
          <div className="font-mono text-xs text-emerald-400 tracking-wider flex items-center gap-2 animate-fadeIn">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            CONVERGED // Unified Multimodal Latent Space Generated [Tensor: (1, 2048)]
          </div>
        )}
      </div>
    </section>
  );
};
