import React, { useState } from 'react';

interface ApiEndpoint {
  method: 'POST' | 'GET';
  path: string;
  badgeBg: string;
  badgeText: string;
  desc: string;
  requestSample: string;
  responseSample: string;
}

const ENDPOINTS: ApiEndpoint[] = [
  {
    method: 'POST',
    path: '/api/v2/analyze/image',
    badgeBg: 'bg-[#00f2fe]/20',
    badgeText: 'text-[#00f2fe]',
    desc: 'DICOM Patch → Token',
    requestSample: '{\n  "dicom_b64": "UklGRiQAAABXRUJQVlA4...",\n  "window_level": [-600, 1500],\n  "de_identify": true\n}',
    responseSample: '{\n  "patch_tokens": [1, 576, 1152],\n  "saliency_coordinates": {"x": 420, "y": 680},\n  "latency_ms": 42.1\n}'
  },
  {
    method: 'POST',
    path: '/api/v2/analyze/speech',
    badgeBg: 'bg-[#e2d4ff]/20',
    badgeText: 'text-[#d0bcff]',
    desc: 'Acoustic Dyspnea Extractor',
    requestSample: '{\n  "audio_clip_wav": "UklGRiQAAABX...",\n  "sample_rate_hz": 16000\n}',
    responseSample: '{\n  "dyspnea_index": "SEVERE",\n  "burst_rate_bpm": 28,\n  "stridor_detected": true,\n  "latency_ms": 31.4\n}'
  },
  {
    method: 'POST',
    path: '/api/v2/analyze/clinical',
    badgeBg: 'bg-[#b4c5ff]/20',
    badgeText: 'text-[#b4c5ff]',
    desc: 'FHIR Labs & Longitudinal',
    requestSample: '{\n  "patient_id": "PT-4921",\n  "fhir_bundle_json": { ... }\n}',
    responseSample: '{\n  "tabular_prior": [1, 64],\n  "normalized_crp": 42.4,\n  "hypoxemia_risk": 0.88\n}'
  },
  {
    method: 'POST',
    path: '/api/v2/analyze/multimodal',
    badgeBg: 'bg-emerald-400/20',
    badgeText: 'text-emerald-400',
    desc: 'Full Cross-Attention Latent',
    requestSample: '{\n  "case_id": "#MED-2025-0941",\n  "weights": {"image": 0.45, "speech": 0.25, "ehr": 0.30}\n}',
    responseSample: '{\n  "latent_representation": [1, 2048],\n  "cross_attention_entropy": 0.042,\n  "confidence": 0.894\n}'
  },
  {
    method: 'POST',
    path: '/api/v2/retrieve/evidence',
    badgeBg: 'bg-[#00f2fe]/20',
    badgeText: 'text-[#00f2fe]',
    desc: 'FAISS Top-K PubMed Search',
    requestSample: '{\n  "latent_query": [1, 2048],\n  "top_k": 3,\n  "societies": ["ATS", "ACC", "AHA"]\n}',
    responseSample: '{\n  "citations": [\n    {"pmid": 3829104, "guideline": "ATS 2024", "relevance": 0.942}\n  ]\n}'
  },
  {
    method: 'POST',
    path: '/api/v2/generate/report',
    badgeBg: 'bg-emerald-400/20',
    badgeText: 'text-emerald-400',
    desc: 'Encrypted Clinical PDF',
    requestSample: '{\n  "case_id": "#MED-2025-0941",\n  "attending_signature_token": "sig_sarah_chen_0x9f..."\n}',
    responseSample: '{\n  "dossier_pdf_url": "https://vault.medexplain.ai/reports/0x9f82.pdf",\n  "sha256": "9f823b1a8d..."\n}'
  }
];

interface ApiEthicsSectionProps {
  onStartAnalysis: () => void;
  onOpenWhitepaper: () => void;
}

export const ApiEthicsSection: React.FC<ApiEthicsSectionProps> = ({
  onStartAnalysis,
  onOpenWhitepaper
}) => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);

  return (
    <section className="relative z-10 w-full py-16 my-8">
      {/* 3 Pillars of Transparent AI */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="p-6 rounded-2xl bg-[#080e1a]/70 border border-[#00f2fe]/20 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-[#00f2fe]/10 text-[#00f2fe] flex items-center justify-center mb-3">
            <span className="material-symbols-outlined">timeline</span>
          </div>
          <h4 className="font-headline text-lg font-semibold text-[#dde2f3]">1. Total Traceability</h4>
          <p className="font-body text-xs text-[#b9cacb] mt-2 leading-relaxed">
            Every inference links back to source image voxels, speech spectrogram intervals, and peer-reviewed PubMed identifiers.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#080e1a]/70 border border-[#b4c5ff]/20 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-[#b4c5ff]/10 text-[#b4c5ff] flex items-center justify-center mb-3">
            <span className="material-symbols-outlined">donut_large</span>
          </div>
          <h4 className="font-headline text-lg font-semibold text-[#dde2f3]">2. Uncertainty Quantification</h4>
          <p className="font-body text-xs text-[#b9cacb] mt-2 leading-relaxed">
            Explicit decomposition of epistemic vs. aleatoric risk prevents high-confidence hallucination in out-of-distribution presentations.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#080e1a]/70 border border-emerald-400/20 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-emerald-400/10 text-emerald-400 flex items-center justify-center mb-3">
            <span className="material-symbols-outlined">supervised_user_circle</span>
          </div>
          <h4 className="font-headline text-lg font-semibold text-[#dde2f3]">3. Human-in-the-Loop Gate</h4>
          <p className="font-body text-xs text-[#b9cacb] mt-2 leading-relaxed">
            Designed strictly as a decision-support aid. Every high-stakes finding mandates physician validation before chart committing.
          </p>
        </div>
      </div>

      {/* API Service Architecture Endpoints Showcase */}
      <div className="p-6 md:p-8 rounded-3xl bg-[#080e1a]/90 border border-[#3a494b]/30 backdrop-blur-2xl mb-12">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#3a494b]/30 mb-4 gap-2">
          <div>
            <span className="font-mono text-xs text-[#00f2fe] uppercase font-semibold">
              DEVELOPER &amp; HOSPITAL PACS INTEGRATION
            </span>
            <h3 className="font-headline text-lg font-semibold text-[#dde2f3]">
              RESTful &amp; gRPC Clinical Endpoints
            </h3>
          </div>
          <span className="font-mono text-xs text-[#849495]">SWAGGER v3 // FHIR COMPLIANT</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
          {ENDPOINTS.map((ep) => (
            <div
              key={ep.path}
              onClick={() => setSelectedEndpoint(ep)}
              className="p-3.5 rounded-xl bg-[#161c28] border border-[#3a494b]/20 hover:border-[#00f2fe]/40 hover:bg-[#1a202c] transition-all flex items-center justify-between cursor-pointer group"
            >
              <div className="flex items-center gap-2.5">
                <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${ep.badgeBg} ${ep.badgeText}`}>
                  {ep.method}
                </span>
                <span className="text-[#dde2f3] group-hover:text-[#00f2fe] transition-colors">
                  {ep.path}
                </span>
              </div>
              <span className="text-[#849495] text-[11px]">{ep.desc}</span>
            </div>
          ))}
        </div>

        {/* Selected Endpoint Preview */}
        {selectedEndpoint && (
          <div className="mt-4 p-4 rounded-xl bg-[#161c28] border border-[#00f2fe]/30 animate-fadeIn">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-[#00f2fe] font-bold">
                API CONTRACT TESTER: {selectedEndpoint.path}
              </span>
              <button
                onClick={() => setSelectedEndpoint(null)}
                className="text-xs font-mono text-[#849495] hover:text-[#dde2f3] cursor-pointer"
              >
                Close
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="text-[10px] font-mono text-[#849495] block mb-1 uppercase">Sample Payload:</span>
                <pre className="p-2 rounded bg-[#080e1a] text-[#b9cacb] font-mono text-[11px] overflow-x-auto border border-[#3a494b]/20">
                  {selectedEndpoint.requestSample}
                </pre>
              </div>
              <div>
                <span className="text-[10px] font-mono text-[#849495] block mb-1 uppercase">Response Tensor:</span>
                <pre className="p-2 rounded bg-[#080e1a] text-[#6ff6ff] font-mono text-[11px] overflow-x-auto border border-[#3a494b]/20">
                  {selectedEndpoint.responseSample}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Grand Final CTA Banner */}
      <div className="relative w-full p-8 md:p-12 rounded-3xl bg-gradient-to-br from-[#242a36] via-[#1a202c] to-[#080e1a] border border-[#00f2fe]/40 text-center flex flex-col items-center justify-center overflow-hidden shadow-[0_0_80px_rgba(0,242,254,0.15)]">
        <div className="absolute inset-0 bg-[#00f2fe]/5 pointer-events-none"></div>

        <div className="relative z-10 max-w-2xl flex flex-col items-center">
          <span className="font-mono text-xs text-[#00f2fe] uppercase tracking-widest mb-2 font-bold">
            RESEARCH PARTNERSHIP INVITATION
          </span>
          <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl font-bold text-[#dde2f3]">
            From Multimodal Data to Explainable Intelligence.
          </h2>
          <p className="font-body text-sm sm:text-base text-[#b9cacb] mt-3 mb-6 leading-relaxed">
            Join academic medical centers, clinical neural laboratories, and diagnostic imaging departments deploying grounded AI verification.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={onStartAnalysis}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-[#00f2fe] to-[#0053db] text-[#080e1a] font-headline text-sm font-bold tracking-wide shadow-[0_0_30px_rgba(0,242,254,0.4)] hover:shadow-[0_0_45px_rgba(0,242,254,0.6)] transition-all cursor-pointer active:scale-95"
            >
              Launch Research Demo Case
            </button>

            <button
              onClick={onOpenWhitepaper}
              className="px-5 py-3.5 rounded-xl bg-[#080e1a]/80 border border-[#3a494b]/40 hover:border-[#00f2fe] text-[#dde2f3] font-headline text-xs sm:text-sm transition-all flex items-center gap-2 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">menu_book</span>
              Read Whitepaper (PDF)
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
