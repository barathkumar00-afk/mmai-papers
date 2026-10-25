import React, { useState } from 'react';

export const FusionSection: React.FC = () => {
  const [fusionMode, setFusionMode] = useState<'cross' | 'tensor'>('cross');

  return (
    <section id="multimodal-fusion" className="relative z-10 w-full py-16 my-8">
      <div className="p-6 md:p-10 rounded-3xl bg-[#080e1a]/85 border border-[#00f2fe]/20 backdrop-blur-2xl relative overflow-hidden">
        {/* Ambient fusion glow */}
        <div className="absolute -right-24 -top-24 w-96 h-96 bg-[#00f2fe]/10 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Text & Control Pane */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-[#00f2fe]/10 border border-[#00f2fe]/30 w-fit">
              <span className="material-symbols-outlined text-[14px] text-[#00f2fe]">hub</span>
              <span className="font-mono text-xs text-[#e0fdff] uppercase font-semibold">MULTIMODAL FUSION MATRIX</span>
            </div>

            <h2 className="font-headline text-2xl sm:text-3xl text-[#dde2f3] font-bold">
              Cross-Attention That Preserves Modality Grounding.
            </h2>

            <p className="font-body text-sm text-[#b9cacb] leading-relaxed">
              Traditional early or late fusion discards modality-specific confidence intervals. MedExplain introduces a calibrated Hierarchical Cross-Attention mechanism where vision queries speech, and both are grounded by clinical biochemistry.
            </p>

            {/* Toggle Architecture Mode */}
            <div className="flex items-center gap-2 p-1 rounded-xl bg-[#242a36] border border-[#3a494b]/30 w-fit mt-1">
              <button
                onClick={() => setFusionMode('cross')}
                className={`px-4 py-2 rounded-lg font-headline text-xs font-semibold transition-all cursor-pointer ${
                  fusionMode === 'cross'
                    ? 'bg-[#00f2fe] text-[#080e1a] shadow-sm'
                    : 'text-[#b9cacb] hover:text-[#dde2f3]'
                }`}
              >
                Cross-Attention Matrix
              </button>
              <button
                onClick={() => setFusionMode('tensor')}
                className={`px-4 py-2 rounded-lg font-headline text-xs font-semibold transition-all cursor-pointer ${
                  fusionMode === 'tensor'
                    ? 'bg-[#00f2fe] text-[#080e1a] shadow-sm'
                    : 'text-[#b9cacb] hover:text-[#dde2f3]'
                }`}
              >
                Tensor Fusion Network
              </button>
            </div>

            <div className="p-4 rounded-xl bg-[#161c28] border border-[#3a494b]/30 font-mono text-xs text-[#b9cacb] space-y-2 mt-1">
              <div className="flex items-center justify-between text-[#dde2f3] font-semibold">
                <span>LATENT PROJECTION:</span>
                <span className="text-[#00f2fe]">
                  {fusionMode === 'cross' ? '[1, 2048] Dense Core' : '[1, 4096] Outer Tensor'}
                </span>
              </div>
              <p>
                {fusionMode === 'cross'
                  ? 'Queries from Qwen2.5-VL attend directly to tokenized acoustic embeddings from Whisper-v3, cross-weighted by tabular clinical risk priors.'
                  : 'Outer-product tensor contraction combines unimodal feature tensors into a high-dimensional joint tensor, capturing 3-way interactions.'}
              </p>
            </div>
          </div>

          {/* Visual Interactive Fusion Core Diagram */}
          <div className="lg:col-span-7 flex flex-col items-center justify-center p-4 relative min-h-[380px]">
            <div className="relative w-full max-w-[480px] h-[340px] flex items-center justify-center">
              {/* Inflowing Stream 1: Visual */}
              <div className="absolute left-0 top-6 flex items-center gap-2 animate-pulse">
                <span className="px-2.5 py-1 rounded bg-[#00f2fe]/20 border border-[#00f2fe]/50 font-mono text-xs text-[#6ff6ff] font-semibold shadow-sm">
                  VISUAL (Qwen-VL)
                </span>
                <span className="w-12 h-0.5 bg-gradient-to-r from-[#00f2fe] to-transparent"></span>
              </div>

              {/* Inflowing Stream 2: Audio */}
              <div className="absolute left-0 bottom-6 flex items-center gap-2">
                <span className="px-2.5 py-1 rounded bg-[#e2d4ff]/20 border border-[#e2d4ff]/50 font-mono text-xs text-[#d0bcff] font-semibold shadow-sm">
                  SPEECH (Whisper)
                </span>
                <span className="w-12 h-0.5 bg-gradient-to-r from-[#d0bcff] to-transparent"></span>
              </div>

              {/* Inflowing Stream 3: EHR */}
              <div className="absolute right-0 top-1/2 -translate-y-1/2 flex items-center gap-2 flex-row-reverse">
                <span className="px-2.5 py-1 rounded bg-[#b4c5ff]/20 border border-[#b4c5ff]/50 font-mono text-xs text-[#b4c5ff] font-semibold shadow-sm">
                  EHR (Tabular)
                </span>
                <span className="w-12 h-0.5 bg-gradient-to-l from-[#b4c5ff] to-transparent"></span>
              </div>

              {/* Glowing Central Sphere */}
              <div className="relative z-10 w-44 h-44 rounded-full bg-gradient-to-br from-[#00f2fe]/30 via-[#1a202c] to-[#0053db]/40 border border-[#00f2fe] p-3 flex flex-col items-center justify-center text-center shadow-[0_0_60px_rgba(0,242,254,0.3)] animate-pulse">
                <span className="material-symbols-outlined text-[32px] text-[#00f2fe] mb-1">psychology</span>
                <span className="font-headline text-[13px] font-bold text-[#dde2f3] uppercase tracking-wider">
                  FUSION CORE
                </span>
                <span className="font-mono text-[10px] text-[#00f2fe] font-semibold">
                  {fusionMode === 'cross' ? 'CROSS-ATTN λ=0.84' : 'TENSOR T-PROD ⊗'}
                </span>
                <span className="font-mono text-[9px] text-[#849495] mt-1">ALIGN: 98.4%</span>
              </div>

              {/* Orbiting Particle Rings (SVG) */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 480 340">
                <circle
                  className="animate-[spin_30s_linear_infinite]"
                  cx="240"
                  cy="170"
                  fill="none"
                  r="110"
                  stroke="rgba(0,242,254,0.2)"
                  strokeDasharray="4 6"
                />
                <circle
                  className="animate-[spin_45s_linear_infinite_reverse]"
                  cx="240"
                  cy="170"
                  fill="none"
                  r="145"
                  stroke="rgba(180,197,255,0.15)"
                  strokeDasharray="6 8"
                />
                {/* Converging Path lines */}
                <path d="M 80,45 Q 160,80 200,140" fill="none" stroke="rgba(0,242,254,0.6)" strokeWidth="2" />
                <path d="M 80,295 Q 160,260 200,200" fill="none" stroke="rgba(208,188,255,0.6)" strokeWidth="2" />
                <path d="M 400,170 L 290,170" fill="none" stroke="rgba(180,197,255,0.6)" strokeWidth="2" />
              </svg>
            </div>

            <div className="mt-4 px-4 py-2 rounded bg-[#242a36] font-mono text-xs text-[#00f2fe] text-center border border-[#3a494b]/30">
              Visual (Qwen-VL) + Clinical (Tabular-BERT) + Speech (Whisper-v3) → Unified Latent Space [1, 2048]
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
