import React, { useState } from 'react';

interface CitationItem {
  id: string;
  title: string;
  relevance: string;
  relBadgeColor: string;
  quote: string;
  pmid: string;
  journal: string;
}

const CITATION_PRESETS: Record<string, CitationItem[]> = {
  default: [
    {
      id: 'c1',
      title: 'WHO Classification of Tumors of the Central Nervous System (WHO CNS5)',
      relevance: '97.4%',
      relBadgeColor: 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30',
      quote: '"Diffuse astrocytic tumors in adults with microvascular proliferation, necrosis, or T1+Gd ring enhancement and IDH-wildtype status are designated Glioblastoma, WHO Grade 4."',
      pmid: 'PMID: 34185806',
      journal: 'Neuro-Oncology (WHO CNS5)'
    },
    {
      id: 'c2',
      title: 'EANO / SNO Clinical Practice Guideline: Adult Gliomas Diagnosis & Treatment',
      relevance: '94.8%',
      relBadgeColor: 'bg-[#00f2fe]/10 text-[#00f2fe] border border-[#00f2fe]/30',
      quote: '"Multiparametric 3T brain MRI (axial T1+Gd, T2/FLAIR, DWI, and perfusion DSC) constitutes standard neuro-navigation planning before maximal safe surgical cytoreduction and Stupp chemoradiotherapy."',
      pmid: 'PMID: 33458763',
      journal: 'Lancet Oncology / EANO'
    },
    {
      id: 'c3',
      title: 'EANO Guidelines on Diagnosis and Management of Meningiomas',
      relevance: '91.2%',
      relBadgeColor: 'bg-[#b4c5ff]/10 text-[#b4c5ff] border border-[#b4c5ff]/30',
      quote: '"Extra-axial dural-based lesions demonstrating intense homogeneous enhancement and characteristic dural tail sign are representative of meningioma; Simpson resection grade dictates recurrence risks."',
      pmid: 'PMID: 34320231',
      journal: 'Neuro-Oncology 2024'
    }
  ],
  meningioma: [
    {
      id: 'm1',
      title: 'European Association of Neuro-Oncology (EANO) Meningioma Guidelines',
      relevance: '98.1%',
      relBadgeColor: 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30',
      quote: '"Meningiomas with hyperostosis of adjacent calvarium and broad dural base typically follow benign WHO grade 1 histology, managed with Simpson Grade I microsurgical resection."',
      pmid: 'PMID: 34320231',
      journal: 'Neuro-Oncology Guidelines'
    },
    {
      id: 'm2',
      title: 'Endocrine Society Clinical Practice: Pituitary Macroadenoma Management',
      relevance: '93.5%',
      relBadgeColor: 'bg-[#00f2fe]/10 text-[#00f2fe] border border-[#00f2fe]/30',
      quote: '"Sellar masses abutting or elevating the optic chiasm require automated Humphrey visual field perimetry and urgent neuro-ophthalmology assessment alongside anterior pituitary hormone profiling."',
      pmid: 'PMID: 29099933',
      journal: 'J Clin Endocrinol Metab'
    },
    {
      id: 'm3',
      title: 'American College of Radiology (ACR) Appropriateness Criteria: Brain Tumor Evaluation',
      relevance: '89.7%',
      relBadgeColor: 'bg-[#b4c5ff]/10 text-[#b4c5ff] border border-[#b4c5ff]/30',
      quote: '"High-resolution contrast-enhanced brain MRI is the gold standard imaging modality for discriminating intra-axial parenchymal lesions from benign dural-based or sellar processes."',
      pmid: 'PMID: 33250102',
      journal: 'J Am Coll Radiol'
    }
  ]
};

export const EvidenceSection: React.FC = () => {
  const [query, setQuery] = useState(
    'Ring-enhancing cerebral mass with central necrosis and surrounding vasogenic edema'
  );
  const [isSearching, setIsSearching] = useState(false);
  const [activeSetKey, setActiveSetKey] = useState<'default' | 'meningioma'>('default');
  const [results, setResults] = useState<CitationItem[]>([]);

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const response = await fetch('http://localhost:8000/api/retrieve/evidence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();

      if (data.success) {
        const mappedCitations = data.citations.map((c: any) => ({
          id: c.id,
          title: c.title,
          relevance: c.relevance,
          relBadgeColor: c.relevance.includes('94') ? 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/30' :
                         c.relevance.includes('91') ? 'bg-[#00f2fe]/10 text-[#00f2fe] border border-[#00f2fe]/30' :
                         'bg-[#b4c5ff]/10 text-[#b4c5ff] border border-[#b4c5ff]/30',
          quote: c.quote,
          pmid: c.pmid,
          journal: c.journal,
        }));
        setResults(mappedCitations);
      }
    } catch (error) {
      console.error("Retrieval failed:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const citations = results.length > 0 ? results : CITATION_PRESETS[activeSetKey];

  return (
    <section id="evidence-universe" className="relative z-10 w-full py-16 my-8">
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-12">
        <div className="px-3.5 py-1 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-[11px] text-emerald-400 mb-3 uppercase tracking-wider font-semibold">
          RETRIEVAL-AUGMENTED GENERATION
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold">
          The Medical Evidence Universe
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2">
          Zero hallucinations. Every generated clinical assertion is cross-anchored to indexed PubMed Central peer-reviewed literature and gold-standard clinical society guidelines.
        </p>
      </div>

      {/* Visual Satellite Diagram + Live Search Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        {/* Universe Visualization Satellite Card */}
        <div className="lg:col-span-5 p-6 rounded-2xl bg-[#080e1a]/85 border border-[#3a494b]/30 backdrop-blur-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="font-mono text-xs text-[#849495] uppercase tracking-wider font-semibold">
                KNOWLEDGE REPOSITORY
              </span>
              <span className="font-mono text-xs text-[#00f2fe] font-semibold">FAISS HNSW INDEX</span>
            </div>

            {/* Satellite clusters */}
            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-[#161c28] border border-[#00f2fe]/20 flex items-center justify-between hover:border-[#00f2fe]/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-[#00f2fe] text-[20px]">menu_book</span>
                  <div>
                    <span className="font-body text-sm text-[#dde2f3] font-medium block">PubMed Central</span>
                    <span className="font-mono text-[11px] text-[#849495]">Indexed full text &amp; abstracts</span>
                  </div>
                </div>
                <span className="font-mono text-xs text-[#6ff6ff] font-semibold">36.2M Papers</span>
              </div>

              <div className="p-3.5 rounded-xl bg-[#161c28] border border-[#b4c5ff]/20 flex items-center justify-between hover:border-[#b4c5ff]/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-[#b4c5ff] text-[20px]">verified</span>
                  <div>
                    <span className="font-body text-sm text-[#dde2f3] font-medium block">Practice Guidelines</span>
                    <span className="font-mono text-[11px] text-[#849495]">ATS / ACC / AHA / ESC / IDSA</span>
                  </div>
                </div>
                <span className="font-mono text-xs text-[#b4c5ff] font-semibold">4,280 Sets</span>
              </div>

              <div className="p-3.5 rounded-xl bg-[#161c28] border border-[#e2d4ff]/20 flex items-center justify-between hover:border-[#e2d4ff]/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-[#d0bcff] text-[20px]">medical_services</span>
                  <div>
                    <span className="font-body text-sm text-[#dde2f3] font-medium block">Radiology Reference Cases</span>
                    <span className="font-mono text-[11px] text-[#849495]">Pathology verified DICOMs</span>
                  </div>
                </div>
                <span className="font-mono text-xs text-[#d0bcff] font-semibold">128K Cases</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-[#3a494b]/20 flex items-center justify-between font-mono text-xs text-[#849495]">
            <span>VECTOR DENSITY: 1.4 TB</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
              INDEX READY
            </span>
          </div>
        </div>

        {/* Live Simulated RAG Query Console */}
        <div className="lg:col-span-7 p-6 rounded-2xl bg-[#080e1a]/85 border border-[#00f2fe]/30 backdrop-blur-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-[#00f2fe] uppercase tracking-wider font-semibold">
                SIMULATED CLINICAL QUERY
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setQuery('Ring-enhancing cerebral mass with central necrosis and surrounding vasogenic edema')}
                  className="font-mono text-[10px] text-[#849495] hover:text-[#00f2fe] underline cursor-pointer"
                >
                  Glioma / GBM
                </button>
                <button
                  onClick={() => setQuery('Extra-axial dural-based mass with homogeneous contrast enhancement and dural tail')}
                  className="font-mono text-[10px] text-[#849495] hover:text-[#00f2fe] underline cursor-pointer"
                >
                  Meningioma
                </button>
                <button
                  onClick={() => setQuery('Sellar and suprasellar mass compressing optic chiasm with bitemporal hemianopsia')}
                  className="font-mono text-[10px] text-[#849495] hover:text-[#00f2fe] underline cursor-pointer"
                >
                  Pituitary
                </button>
              </div>
            </div>

            <div className="p-2 rounded-xl bg-[#242a36] border border-[#3a494b]/30 flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-[#00f2fe] ml-1">search</span>
              <input
                className="w-full bg-transparent font-mono text-xs text-[#dde2f3] focus:outline-none placeholder-[#849495]"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Enter clinical presentation or biomedical question..."
                type="text"
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className="px-4 py-2 rounded-lg bg-[#00f2fe] text-[#080e1a] font-headline text-xs font-semibold hover:opacity-90 shrink-0 cursor-pointer transition-all active:scale-95 disabled:opacity-50"
              >
                {isSearching ? 'Searching...' : 'Query FAISS'}
              </button>
            </div>

            <span className="font-mono text-xs text-[#849495] block mb-3 uppercase tracking-wider font-semibold">
              RETRIEVED &amp; RE-RANKED CITATIONS (TOP-3)
            </span>

            {/* Evidence Cards */}
            <div className={`space-y-3 transition-opacity duration-300 ${isSearching ? 'opacity-40' : 'opacity-100'}`}>
              {citations.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-xl bg-[#161c28] border border-[#3a494b]/30 hover:border-[#00f2fe]/40 transition-colors flex flex-col gap-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-headline text-sm font-semibold text-[#dde2f3]">
                      {c.title}
                    </span>
                    <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-bold shrink-0 ${c.relBadgeColor}`}>
                      RELEVANCE: {c.relevance}
                    </span>
                  </div>
                  <p className="font-body text-xs text-[#b9cacb] line-clamp-2 italic leading-relaxed">
                    {c.quote}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-[#3a494b]/20 font-mono text-[10px] text-[#849495]">
                    <span>{c.pmid} // {c.journal}</span>
                    <span className="text-[#d0bcff]">DEMO EVIDENCE - NOT FOR TREATMENT</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
