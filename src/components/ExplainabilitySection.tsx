import React, { useState } from 'react';

export const ExplainabilitySection: React.FC = () => {
  const [sliderVal, setSliderVal] = useState(45);

  const imgShare = sliderVal.toFixed(1);
  const remaining = 100 - sliderVal;
  const speechShare = (remaining * 0.45).toFixed(1);
  const ehrShare = (remaining * 0.55).toFixed(1);
  const confidence = (85 + (sliderVal * 0.1)).toFixed(1);

  return (
    <section id="explainability" className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold">
          AUDITABLE TRACEABILITY
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          "Every Output Must Have an Evidence Trail."
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          Black boxes are unacceptable in medicine. MedExplain breaks clinical inference down into an uninterrupted 5-tier causal chain.
        </p>
      </div>

      {/* 5-Tier Explanation Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 mb-12">
        <div className="p-4 rounded-xl bg-[#161c28] border border-[#00f2fe]/30 flex flex-col items-center text-center">
          <span className="w-8 h-8 rounded-full bg-[#00f2fe]/20 text-[#00f2fe] flex items-center justify-center font-bold font-mono mb-2">
            1
          </span>
          <h5 className="font-headline text-sm font-semibold text-[#dde2f3]">Patient Evidence</h5>
          <span className="font-mono text-[11px] text-[#849495] mt-1">Images, Speech, Vitals</span>
        </div>

        <div className="p-4 rounded-xl bg-[#161c28] border border-[#00f2fe]/30 flex flex-col items-center text-center">
          <span className="w-8 h-8 rounded-full bg-[#00f2fe]/20 text-[#00f2fe] flex items-center justify-center font-bold font-mono mb-2">
            2
          </span>
          <h5 className="font-headline text-sm font-semibold text-[#dde2f3]">Observations</h5>
          <span className="font-mono text-[11px] text-[#849495] mt-1">Ground glass, wheeze, SpO2</span>
        </div>

        <div className="p-4 rounded-xl bg-[#161c28] border border-emerald-400/30 flex flex-col items-center text-center">
          <span className="w-8 h-8 rounded-full bg-emerald-400/20 text-emerald-400 flex items-center justify-center font-bold font-mono mb-2">
            3
          </span>
          <h5 className="font-headline text-sm font-semibold text-[#dde2f3]">Retrieved Lit</h5>
          <span className="font-mono text-[11px] text-[#849495] mt-1">PMID Guidelines verified</span>
        </div>

        <div className="p-4 rounded-xl bg-[#161c28] border border-[#b4c5ff]/30 flex flex-col items-center text-center">
          <span className="w-8 h-8 rounded-full bg-[#b4c5ff]/20 text-[#b4c5ff] flex items-center justify-center font-bold font-mono mb-2">
            4
          </span>
          <h5 className="font-headline text-sm font-semibold text-[#dde2f3]">Reasoning Context</h5>
          <span className="font-mono text-[11px] text-[#849495] mt-1">Multi-factor differential</span>
        </div>

        <div className="p-4 rounded-xl bg-[#1a202c] border border-[#00f2fe] flex flex-col items-center text-center shadow-[0_0_20px_rgba(0,242,254,0.2)]">
          <span className="w-8 h-8 rounded-full bg-[#00f2fe] text-[#080e1a] flex items-center justify-center font-bold font-mono mb-2">
            5
          </span>
          <h5 className="font-headline text-sm font-semibold text-[#6ff6ff]">Clinical Findings</h5>
          <span className="font-mono text-[11px] text-[#00f2fe] mt-1">Non-autonomous advice</span>
        </div>
      </div>

      {/* Side-by-side Traceability Matrix with Dynamic Attention Slider */}
      <div className="p-6 md:p-8 rounded-3xl bg-[#080e1a]/85 border border-[#00f2fe]/20 backdrop-blur-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#3a494b]/30 gap-4 mb-6">
          <div>
            <h3 className="font-headline text-lg sm:text-xl text-[#dde2f3] font-semibold">
              Traceability Matrix // "WHY THIS INTERPRETATION?"
            </h3>
            <p className="font-body text-xs text-[#b9cacb] mt-0.5">
              Adjust modality weighting to observe dynamic cross-attention reallocation.
            </p>
          </div>

          {/* Interactive Weight Sensitivity Slider */}
          <div className="flex items-center gap-3 bg-[#242a36] px-4 py-2 rounded-xl border border-[#3a494b]/30">
            <span className="font-mono text-xs text-[#849495]">IMAGE ATTN SLIDER:</span>
            <input
              type="range"
              min="10"
              max="90"
              value={sliderVal}
              onChange={(e) => setSliderVal(parseInt(e.target.value))}
              className="accent-[#00f2fe] cursor-pointer w-28"
            />
            <span className="font-mono text-xs text-[#00f2fe] font-bold w-10 text-right">
              {sliderVal}%
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Matrix 1 */}
          <div className="p-4 rounded-xl bg-[#161c28] border border-[#00f2fe]/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] font-bold text-[#00f2fe]">[ 01 IMAGE EVIDENCE ]</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
              <p className="font-mono text-xs text-[#dde2f3] font-semibold">Segmental Ground-Glass Attenuation</p>
              <p className="font-body text-xs text-[#b9cacb] mt-1 leading-relaxed">
                Posterior lower lung lobes bilaterally with subpleural sparing. Dice score: 0.91.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-[#3a494b]/20 flex justify-between font-mono text-[11px] text-[#849495]">
              <span>ATTN SHARE</span>
              <span className="text-[#00f2fe] font-bold">{imgShare}%</span>
            </div>
          </div>

          {/* Matrix 2 */}
          <div className="p-4 rounded-xl bg-[#161c28] border border-[#e2d4ff]/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] font-bold text-[#d0bcff]">[ 02 SPEECH SYMPTOM ]</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
              <p className="font-mono text-xs text-[#dde2f3] font-semibold">Acoustic Dyspnea Index</p>
              <p className="font-body text-xs text-[#b9cacb] mt-1 leading-relaxed">
                Tachypneic cadence (respiratory rate ~28 bpm), vocal pause ratio: 38% elevated.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-[#3a494b]/20 flex justify-between font-mono text-[11px] text-[#849495]">
              <span>ATTN SHARE</span>
              <span className="text-[#d0bcff] font-bold">{speechShare}%</span>
            </div>
          </div>

          {/* Matrix 3 */}
          <div className="p-4 rounded-xl bg-[#161c28] border border-[#b4c5ff]/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] font-bold text-[#b4c5ff]">[ 03 CLINICAL CONTEXT ]</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
              <p className="font-mono text-xs text-[#dde2f3] font-semibold">Hypoxemia &amp; Biomarkers</p>
              <p className="font-body text-xs text-[#b9cacb] mt-1 leading-relaxed">
                SpO2 88% on ambient air, CRP 42 mg/L, PaO2/FiO2 estimated at 240 mmHg.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-[#3a494b]/20 flex justify-between font-mono text-[11px] text-[#849495]">
              <span>ATTN SHARE</span>
              <span className="text-[#b4c5ff] font-bold">{ehrShare}%</span>
            </div>
          </div>

          {/* Matrix 4 */}
          <div className="p-4 rounded-xl bg-[#161c28] border border-emerald-400/40 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] font-bold text-emerald-400">[ 04 GROUNDED SOURCE ]</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
              <p className="font-mono text-xs text-[#dde2f3] font-semibold">ATS Guidelines 2024</p>
              <p className="font-body text-xs text-[#b9cacb] mt-1 leading-relaxed">
                Criteria for early non-cardiogenic acute lung injury matched across 4 independent markers.
              </p>
            </div>
            <div className="mt-4 pt-2 border-t border-[#3a494b]/20 flex justify-between font-mono text-[11px] text-emerald-400 font-bold">
              <span>CONFIDENCE</span>
              <span>{confidence}%</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
