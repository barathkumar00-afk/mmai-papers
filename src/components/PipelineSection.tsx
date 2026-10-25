import React, { useState } from 'react';

interface StageSpec {
  stage: number;
  name: string;
  shortDesc: string;
  model: string;
  tagColor: string;
  title: string;
  execTime: string;
  input: string;
  operations: string[];
  output: string;
}

const STAGES: StageSpec[] = [
  {
    stage: 1,
    name: 'Vision Extract',
    shortDesc: 'DICOM De-identification & Patch Tokens',
    model: 'M: Qwen2.5-VL',
    tagColor: 'text-[#00f2fe]',
    title: 'STAGE 01 // VISION EXTRACTOR (Qwen2.5-VL)',
    execTime: '24.1ms',
    input: `{\n  "source": "Sample_CXR_492.dcm",\n  "windowing": "LUNG [-600, 1500 HU]",\n  "patch_grid": [14, 14]\n}`,
    operations: [
      '• De-identification anonymizer applied',
      '• Patch Projection: 1152-dim ViT backbone',
      '• Spatial Bilateral Masking'
    ],
    output: `{\n  "vision_tokens": [1, 576, 1152],\n  "spatial_resolution": "1024x1024",\n  "status": "EXTRACTED"\n}`
  },
  {
    stage: 2,
    name: 'Speech Token',
    shortDesc: '16kHz Mel-Spectrogram + Phonetics',
    model: 'M: Whisper-v3',
    tagColor: 'text-[#d0bcff]',
    title: 'STAGE 02 // SPEECH TOKENIZER (Whisper Large-v3)',
    execTime: '31.4ms',
    input: `{\n  "audio_clip": "16kHz Mono 14.2s",\n  "channels": 1,\n  "snr_db": 24.6\n}`,
    operations: [
      '• 80-channel Log-Mel spectrogram',
      '• Pitch Perturbation & Jitter Profiling',
      '• Speech-to-Pause Dynamic Parsing'
    ],
    output: `{\n  "audio_tokens": [1, 256, 768],\n  "speech_pause_ratio": 0.38,\n  "dyspnea_index": "HIGH"\n}`
  },
  {
    stage: 3,
    name: 'EHR Ingestion',
    shortDesc: 'LOINC/SNOMED Normalization',
    model: 'M: Tabular-BERT',
    tagColor: 'text-[#b4c5ff]',
    title: 'STAGE 03 // EHR CLINICAL INGESTION',
    execTime: '8.7ms',
    input: `{\n  "spo2": 88,\n  "crp": 42.4,\n  "pao2_fio2": 240,\n  "smoker_pack_years": 10\n}`,
    operations: [
      '• LOINC code unification',
      '• Quantile biomarker normalization',
      '• Comorbidity embedding mapping'
    ],
    output: `{\n  "tabular_prior": [1, 64],\n  "hypoxemic_tier": "SEVERE",\n  "cardiac_risk": 0.08\n}`
  },
  {
    stage: 4,
    name: 'Alignment',
    shortDesc: 'Contrastive Temporal Cross-Lock',
    model: 'M: MedContrast-7B',
    tagColor: 'text-[#849495]',
    title: 'STAGE 04 // CROSS-MODAL ALIGNMENT LOCK',
    execTime: '14.2ms',
    input: `{\n  "vision_dim": 1152,\n  "audio_dim": 768,\n  "ehr_dim": 64\n}`,
    operations: [
      '• Contrastive InfoNCE Loss Minimization',
      '• Modality Temperature Scaling (tau=0.05)',
      '• Cross-Projection to Shared Manifold'
    ],
    output: `{\n  "aligned_state": true,\n  "cosine_similarity": 0.941,\n  "temporal_drift": "0.02s"\n}`
  },
  {
    stage: 5,
    name: 'Multimodal Fusion',
    shortDesc: 'Cross-Attention Latent Projection',
    model: 'M: CrossAttn Core',
    tagColor: 'text-[#00f2fe]',
    title: 'STAGE 05 // MULTIMODAL FUSION CORE INSPECTOR',
    execTime: '18.2ms',
    input: `{\n  "vision_tokens": [1, 576, 1152],\n  "audio_tokens": [1, 256, 768],\n  "tabular_prior": [1, 64]\n}`,
    operations: [
      '• Scaled Dot-Product Cross Attention',
      '• Temperature Coefficient τ = 0.07',
      '• Dropout Rate = 0.10 (Clinical Dropout)'
    ],
    output: `{\n  "latent_representation": [1, 2048],\n  "entropy_score": 0.042,\n  "confidence": 0.894\n}`
  },
  {
    stage: 6,
    name: 'FAISS Index',
    shortDesc: 'HNSW Cosine Vector Retrieval',
    model: 'M: HNSW 384-dim',
    tagColor: 'text-emerald-400',
    title: 'STAGE 06 // FAISS VECTOR DATABASE RETRIEVER',
    execTime: '4.8ms',
    input: `{\n  "query_embedding": [1, 1536],\n  "top_k": 50,\n  "index_type": "HNSW32_SQ8"\n}`,
    operations: [
      '• Exact nearest centroid probing',
      '• Beam search depth M=32, efSearch=64',
      '• 36.2M biomedical documents traversed'
    ],
    output: `{\n  "candidate_pmids": 50,\n  "nearest_distance": 0.124,\n  "latency_ms": 4.8\n}`
  },
  {
    stage: 7,
    name: 'RAG Synthesis',
    shortDesc: 'PubMed Top-K Context Grounding',
    model: 'M: Re-ranker v2',
    tagColor: 'text-emerald-400',
    title: 'STAGE 07 // RAG RE-RANKER & CITATION PACKER',
    execTime: '12.5ms',
    input: `{\n  "candidates_count": 50,\n  "cross_encoder": "BioBERT-v2",\n  "grounding_threshold": 0.85\n}`,
    operations: [
      '• Cross-encoder pair re-ranking',
      '• Top-3 verified guideline selection',
      '• Conflict detection against Gold Standard'
    ],
    output: `{\n  "ranked_citations": 3,\n  "top_guideline": "ATS_2024_AHRF",\n  "relevance_score": 0.942\n}`
  },
  {
    stage: 8,
    name: 'LLM Reasoner',
    shortDesc: 'Clinical Differential Logic',
    model: 'M: Llama-3.1-70B',
    tagColor: 'text-[#b4c5ff]',
    title: 'STAGE 08 // CLINICAL DIFFERENTIAL REASONING',
    execTime: '48.6ms',
    input: `{\n  "context_tokens": 4210,\n  "guidelines_included": 3,\n  "temperature": 0.1\n}`,
    operations: [
      '• Tree-of-Thought clinical path expansion',
      '• Negative marker rejection (Troponin-I Neg)',
      '• Probability mass normalization'
    ],
    output: `{\n  "primary_differential": "Acute Pneumonitis",\n  "probability": 0.642,\n  "secondary_tier": "ARDS Mild"\n}`
  },
  {
    stage: 9,
    name: 'Explainability',
    shortDesc: 'Attention attribution heatmaps',
    model: 'M: GradCAM + Trace',
    tagColor: 'text-[#00f2fe]',
    title: 'STAGE 09 // EXPLAINABILITY & SALIENCY MAPPER',
    execTime: '15.9ms',
    input: `{\n  "feature_maps": [1, 64, 32, 32],\n  "target_class": "Pneumonitis",\n  "gradients": "ACTIVE"\n}`,
    operations: [
      '• GradCAM saliency backpropagation',
      '• Vocal pause attention attribution',
      '• Modality weight decomposition (45/25/30)'
    ],
    output: `{\n  "heatmap_matrix": "1024x1024 float16",\n  "saliency_peak": "R_Base_Zone",\n  "audit_trail_valid": true\n}`
  },
  {
    stage: 10,
    name: 'Report Gen',
    shortDesc: 'Structured PDF + Attending Gate',
    model: 'OUTPUT READY',
    tagColor: 'text-emerald-400',
    title: 'STAGE 10 // CLINICAL DOSSIER BINDING & SIGN-OFF',
    execTime: '6.2ms',
    input: `{\n  "all_stages_completed": true,\n  "case_id": "#MED-2025-0941",\n  "crypto_salt": "0x9f823b1a"\n}`,
    operations: [
      '• FHIR Bundle JSON serialization',
      '• Attending physician digital signature lock',
      '• SHA-256 cryptographic dossier seal'
    ],
    output: `{\n  "dossier_hash": "0x9f82...3b1a",\n  "status": "AWAITING_PHYSICIAN_SIGNATURE",\n  "exportable_pdf": true\n}`
  }
];

export const PipelineSection: React.FC = () => {
  const [selectedStageIndex, setSelectedStageIndex] = useState(4); // Default to Stage 05 (Fusion Core)
  const currentStage = STAGES[selectedStageIndex];

  return (
    <section id="architecture" className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold">
          END-TO-END WORKFLOW
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          10-Stage Auditable Clinical Pipeline
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          Every inference step is deterministic, auditable, and decoupled. Select any pipeline node to inspect real-time tensor contracts and data shapes.
        </p>
      </div>

      {/* Horizontal Scrollable Pipeline Track */}
      <div className="w-full overflow-x-auto pb-6">
        <div className="min-w-[1280px] grid grid-cols-10 gap-3 relative py-4">
          {STAGES.map((s, idx) => {
            const isSelected = selectedStageIndex === idx;
            return (
              <div
                key={s.stage}
                onClick={() => setSelectedStageIndex(idx)}
                className={`cursor-pointer group p-3 rounded-xl transition-all flex flex-col justify-between h-48 border ${
                  isSelected
                    ? 'bg-[#1a202c] border-[#00f2fe] shadow-[0_0_18px_rgba(0,242,254,0.25)] scale-[1.03]'
                    : 'bg-[#161c28] border-[#3a494b]/30 hover:border-[#00f2fe]/60 hover:bg-[#1a202c]'
                }`}
              >
                <div>
                  <span className={`font-mono text-xs font-bold ${s.tagColor}`}>
                    STAGE 0{s.stage < 10 ? `0${s.stage}` : s.stage}
                  </span>
                  <h4 className="font-headline text-sm font-bold text-[#dde2f3] mt-1 group-hover:text-[#00f2fe] transition-colors leading-tight">
                    {s.name}
                  </h4>
                  <p className="font-mono text-[11px] text-[#b9cacb] mt-1 line-clamp-2">
                    {s.shortDesc}
                  </p>
                </div>
                <div className="font-mono text-[10px] text-[#849495] border-t border-[#3a494b]/20 pt-1 flex items-center justify-between">
                  <span>{s.model}</span>
                  {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-[#00f2fe] animate-ping" />}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Pipeline Inspection Drawer */}
      <div className="mt-4 p-6 md:p-8 rounded-2xl bg-[#080e1a]/95 border border-[#00f2fe]/30 backdrop-blur-xl shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#3a494b]/30 mb-4 gap-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#00f2fe]">terminal</span>
            <span className="font-mono text-sm sm:text-base text-[#e0fdff] font-semibold">
              {currentStage.title}
            </span>
          </div>
          <span className="font-mono text-xs text-emerald-400 font-semibold">
            EXEC_TIME: {currentStage.execTime} // STATUS: OK
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <span className="font-mono text-xs text-[#849495] block mb-1 uppercase tracking-wider font-semibold">
              INPUT SPECIFICATION
            </span>
            <pre className="p-3 rounded bg-[#1a202c] font-mono text-xs text-[#b9cacb] overflow-x-auto border border-[#3a494b]/30 leading-relaxed">
              {currentStage.input}
            </pre>
          </div>

          <div>
            <span className="font-mono text-xs text-[#849495] block mb-1 uppercase tracking-wider font-semibold">
              OPERATIONAL MATRIX
            </span>
            <div className="p-3 rounded bg-[#1a202c] font-mono text-xs text-[#b9cacb] space-y-2 border border-[#3a494b]/30 min-h-[90px]">
              {currentStage.operations.map((op, i) => (
                <p key={i}>{op}</p>
              ))}
            </div>
          </div>

          <div>
            <span className="font-mono text-xs text-[#849495] block mb-1 uppercase tracking-wider font-semibold">
              EMBEDDING OUTPUT
            </span>
            <pre className="p-3 rounded bg-[#1a202c] font-mono text-xs text-[#6ff6ff] overflow-x-auto border border-[#3a494b]/30 leading-relaxed">
              {currentStage.output}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
};
