import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { FragmentedSection } from './components/FragmentedSection';
import { FusionSection } from './components/FusionSection';
import { PipelineSection } from './components/PipelineSection';
import { EvidenceSection } from './components/EvidenceSection';
import { ExplainabilitySection } from './components/ExplainabilitySection';
import { WorkbenchSection } from './components/WorkbenchSection';
import { ReportSection } from './components/ReportSection';
import { ModelStackSection } from './components/ModelStackSection';
import { ApiEthicsSection } from './components/ApiEthicsSection';
import { FooterBar } from './components/FooterBar';
import { PdfModal, TraceModal, WhitepaperModal } from './components/Modals';

export default function App() {
  const [activeTab, setActiveTab] = useState('platform');
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [isTraceModalOpen, setIsTraceModalOpen] = useState(false);
  const [isWhitepaperModalOpen, setIsWhitepaperModalOpen] = useState(false);

  // Scroll spy to highlight active nav tab
  useEffect(() => {
    const handleScroll = () => {
      const sections = [
        { id: 'platform', el: document.getElementById('platform') },
        { id: 'architecture', el: document.getElementById('architecture') },
        { id: 'multimodal-fusion', el: document.getElementById('multimodal-fusion') },
        { id: 'evidence-universe', el: document.getElementById('evidence-universe') },
        { id: 'explainability', el: document.getElementById('explainability') },
        { id: 'interactive-demo', el: document.getElementById('workbench-simulator') },
        { id: 'clinical-report', el: document.getElementById('clinical-report') }
      ];

      const scrollPos = window.scrollY + 200;

      for (let i = sections.length - 1; i >= 0; i--) {
        const sec = sections[i];
        if (sec.el && sec.el.offsetTop <= scrollPos) {
          setActiveTab(sec.id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToWorkbench = () => {
    setActiveTab('interactive-demo');
    const el = document.getElementById('workbench-simulator');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToArchitecture = () => {
    setActiveTab('architecture');
    const el = document.getElementById('architecture');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToEvidence = () => {
    setActiveTab('evidence-universe');
    const el = document.getElementById('evidence-universe');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="bg-[#0e131f] font-body text-[#dde2f3] min-h-screen selection:bg-[#00f2fe] selection:text-[#080e1a] relative overflow-x-hidden">
      {/* AMBIENT CLINICAL GLOW BACKDROPS */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="absolute -top-40 left-1/4 w-[700px] h-[700px] bg-[#00f2fe]/5 rounded-full blur-[140px]" />
        <div className="absolute top-[40%] right-[-100px] w-[600px] h-[600px] bg-[#0053db]/10 rounded-full blur-[160px]" />
        <div className="absolute bottom-[20%] left-[-50px] w-[500px] h-[500px] bg-[#e2d4ff]/5 rounded-full blur-[140px]" />
      </div>

      {/* FIXED TOP NAVIGATION */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLaunchAnalysis={scrollToWorkbench}
      />

      {/* MAIN CONTENT RUNTIME */}
      <main className="relative z-10 w-full px-4 sm:px-8 max-w-[1440px] mx-auto pb-16">
        {/* Section 1: Hero with 3D Manifold */}
        <HeroSection
          onStartAnalysis={scrollToWorkbench}
          onExploreArchitecture={scrollToArchitecture}
          onExploreEvidence={scrollToEvidence}
        />

        {/* Section 2: The Problem — Fragmented Clinical Information */}
        <FragmentedSection />

        {/* Section 3: Multimodal Fusion Architecture */}
        <FusionSection />

        {/* Section 4: 10-Stage Auditable Clinical Pipeline */}
        <PipelineSection />

        {/* Section 5: Medical Evidence Universe (RAG Grounding) */}
        <EvidenceSection />

        {/* Section 6: Explainability Engine */}
        <ExplainabilitySection />

        {/* Section 7: Live Workbench Simulator */}
        <WorkbenchSection />

        {/* Section 8: 3D Floating Clinical Report */}
        <ReportSection
          onOpenPdfModal={() => setIsPdfModalOpen(true)}
          onOpenTraceModal={() => setIsTraceModalOpen(true)}
        />

        {/* Section 9: Model Stack Specification */}
        <ModelStackSection />

        {/* Section 10: Transparency, Ethics & API Spec */}
        <ApiEthicsSection
          onStartAnalysis={scrollToWorkbench}
          onOpenWhitepaper={() => setIsWhitepaperModalOpen(true)}
        />
      </main>

      {/* Persistent Clinical Decision Support Disclaimer Footer */}
      <FooterBar />

      {/* INTERACTIVE MODALS */}
      <PdfModal
        isOpen={isPdfModalOpen}
        onClose={() => setIsPdfModalOpen(false)}
      />

      <TraceModal
        isOpen={isTraceModalOpen}
        onClose={() => setIsTraceModalOpen(false)}
      />

      <WhitepaperModal
        isOpen={isWhitepaperModalOpen}
        onClose={() => setIsWhitepaperModalOpen(false)}
      />
    </div>
  );
}
