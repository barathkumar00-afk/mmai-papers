import React, { useState } from 'react';

interface ModelItem {
  id: string;
  name: string;
  category: string;
  categoryColor: string;
  icon: string;
  desc: string;
  paramLabel: string;
  latencyLabel: string;
  expandedDetails: string;
}

const MODELS: ModelItem[] = [
  {
    id: 'qwen',
    name: 'Qwen2.5-VL',
    category: 'VISION-LANG',
    categoryColor: 'text-[#00f2fe] bg-[#00f2fe]/10',
    icon: 'image_search',
    desc: 'Visual encoder adapted for high-resolution Brain MRI slices (T1+Gd, T2/FLAIR, DWI), extracting spatial patch embeddings for intracranial lesions.',
    paramLabel: 'PARAMS: 7B / 72B',
    latencyLabel: '42ms INFERENCE',
    expandedDetails: 'Evaluated on Figshare Brain Tumor and BraTS benchmarks. Employs dynamic resolution windowing with Hounsfield/intensity rescaling for gliomas, meningiomas, and pituitary lesions.'
  },
  {
    id: 'whisper',
    name: 'Whisper Large-v3',
    category: 'ACOUSTIC NLP',
    categoryColor: 'text-[#d0bcff] bg-[#e2d4ff]/10',
    icon: 'mic',
    desc: 'Phonetic analysis engine capturing spectral frequency variations, cognitive speech pausing latencies, and dysarthria cadences.',
    paramLabel: 'TOKEN: 16kHz MEL',
    latencyLabel: 'WER < 2.1%',
    expandedDetails: 'Features specialized speech hesitation and cognitive latency encoders, detecting neuromotor speech slowing, articulatory imprecision, and phonetic pausing.'
  },
  {
    id: 'llama',
    name: 'Llama 3.1 70B',
    category: 'REASONING CORE',
    categoryColor: 'text-[#b4c5ff] bg-[#b4c5ff]/10',
    icon: 'psychology',
    desc: 'Grounded clinical reasoner synthesizing retrieved medical literature with fused multimodal embeddings via tree-of-thought verification.',
    paramLabel: 'CONTEXT: 128K',
    latencyLabel: 'QUANT: 4-BIT AWQ',
    expandedDetails: 'Fine-tuned using clinical chain-of-thought feedback from 12 hospital ICU networks. Enforces strict zero-hallucination guardrails via citation cross-anchoring.'
  },
  {
    id: 'faiss',
    name: 'FAISS HNSW Index',
    category: 'VECTOR DB',
    categoryColor: 'text-emerald-400 bg-emerald-400/10',
    icon: 'data_object',
    desc: 'Microsecond-scale approximate nearest neighbor retrieval indexing 36M PubMed abstracts and gold-standard societal guidelines.',
    paramLabel: 'LATENCY: 4.8ms',
    latencyLabel: 'DIM: 1536',
    expandedDetails: 'Operates with hierarchical NSW graph clusters on NVMe flash arrays. Cosine similarity thresholding filters out weakly matched biomedical evidence.'
  },
  {
    id: 'pubmed',
    name: 'Medical Evidence Base',
    category: 'KNOWLEDGE BASE',
    categoryColor: 'text-[#00f2fe] bg-[#00f2fe]/10',
    icon: 'library_books',
    desc: 'Continuously reconciled clinical literature repository enriched with semantic ontologies (MeSH, UMLS, ICD-11, LOINC).',
    paramLabel: 'DOCS: 40M+',
    latencyLabel: 'WEEKLY REFRESH',
    expandedDetails: 'Semantic graph synchronizes with NLM PubMed Central nightly, indexing emergent RCTs, FDA safety communications, and updated clinical society practice bulletins.'
  },
  {
    id: 'fusion',
    name: 'MedExplain Fusion Core',
    category: 'CROSS-ATTENTION',
    categoryColor: 'text-[#00f2fe] bg-[#00f2fe]/20',
    icon: 'all_inclusive',
    desc: 'Proprietary cross-modal alignment layer establishing spatial-to-acoustic-to-biochemical coherence without catastrophic forgetting.',
    paramLabel: 'LATENT: [1, 2048]',
    latencyLabel: 'ZERO FORGETTING',
    expandedDetails: 'Trained with contrastive InfoNCE objectives. Automatically re-weights missing or noisy modalities to safeguard clinical calibration during telemetry dropouts.'
  }
];

export const ModelStackSection: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <section className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold">
          COMPUTATIONAL ARCHITECTURE
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          The MedExplain Model Stack
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          A coordinated multi-agent ecosystem engineered with high parameter efficiency and low clinical latency.
        </p>
      </div>

      {/* 6 Interactive Spec Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {MODELS.map((m) => {
          const isSelected = selectedId === m.id;
          return (
            <div
              key={m.id}
              onClick={() => setSelectedId(isSelected ? null : m.id)}
              className={`p-6 rounded-2xl bg-[#161c28]/80 border transition-all duration-300 backdrop-blur-xl flex flex-col justify-between cursor-pointer ${
                isSelected
                  ? 'border-[#00f2fe] shadow-[0_0_30px_rgba(0,242,254,0.25)] scale-[1.02]'
                  : 'border-[#00f2fe]/20 hover:border-[#00f2fe]/50'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`p-2 rounded-lg material-symbols-outlined ${m.categoryColor}`}>
                    {m.icon}
                  </span>
                  <span className="font-mono text-xs font-semibold text-[#00f2fe]">
                    {m.category}
                  </span>
                </div>
                <h4 className="font-headline text-lg font-semibold text-[#dde2f3]">{m.name}</h4>
                <p className="font-body text-xs text-[#b9cacb] mt-1.5 leading-relaxed">{m.desc}</p>

                {isSelected && (
                  <div className="mt-3 p-3 rounded-lg bg-[#080e1a] border border-[#00f2fe]/30 font-mono text-[11px] text-[#6ff6ff] animate-fadeIn">
                    {m.expandedDetails}
                  </div>
                )}
              </div>

              <div className="mt-5 pt-2 border-t border-[#3a494b]/20 font-mono text-xs text-[#849495] flex justify-between items-center">
                <span>{m.paramLabel}</span>
                <span className="text-[#00f2fe] font-semibold">{m.latencyLabel}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
