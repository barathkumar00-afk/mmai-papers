import React, { useState } from 'react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLaunchAnalysis: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onLaunchAnalysis
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'platform', label: 'Platform', href: '#platform' },
    { id: 'architecture', label: 'Architecture', href: '#architecture' },
    { id: 'multimodal-fusion', label: 'Multimodal Fusion', href: '#multimodal-fusion' },
    { id: 'evidence-universe', label: 'Evidence Universe', href: '#evidence-universe' },
    { id: 'explainability', label: 'Explainability', href: '#explainability' },
    { id: 'interactive-demo', label: 'Interactive Demo', href: '#workbench-simulator' },
    { id: 'clinical-report', label: 'Clinical Report', href: '#clinical-report' }
  ];

  const handleNavClick = (id: string, href: string) => {
    setActiveTab(id);
    setMobileMenuOpen(false);
    const element = document.querySelector(href);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 w-full bg-[#080e1a]/85 backdrop-blur-xl border-b border-[#00f2fe]/20 shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
      <div className="h-16 w-full px-4 md:px-8 flex items-center justify-between gap-4">
        {/* Brand & Technical Protocol Status */}
        <div className="flex items-center gap-3 shrink-0">
          <a
            href="#platform"
            onClick={(e) => {
              e.preventDefault();
              handleNavClick('platform', '#platform');
            }}
            className="flex items-center gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00f2fe] to-[#0053db] flex items-center justify-center shadow-[0_0_12px_rgba(0,242,254,0.3)]">
              <span className="material-symbols-outlined text-[#080e1a] text-[20px] font-bold">clinical_notes</span>
            </div>
            <span className="font-headline font-bold text-lg tracking-tight text-[#dde2f3] group-hover:text-[#00f2fe] transition-colors">
              MedExplain <span className="text-[#00f2fe] text-xs font-mono font-normal">AI</span>
            </span>
          </a>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-[#161c28] border border-[#00f2fe]/30 shadow-[0_0_12px_rgba(0,242,254,0.15)]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00f2fe] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00dce6]"></span>
            </span>
            <span className="font-mono text-[10px] uppercase text-[#e0fdff] tracking-wider font-semibold">
              CLINICAL INTELLIGENCE LAB v2.4 (RESEARCH)
            </span>
          </div>
        </div>

        {/* Desktop Nav Links */}
        <nav className="hidden xl:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id, item.href)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#00f2fe] text-[#080e1a] font-semibold shadow-[0_0_12px_rgba(0,242,254,0.3)]'
                    : 'text-[#b9cacb] hover:text-[#dde2f3] hover:bg-[#1a202c]'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Right Action Items */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded bg-[#080e1a]/90 border border-[#3a494b]/40">
            <span className="material-symbols-outlined text-[14px] text-[#00f2fe]">network_check</span>
            <span className="font-mono text-[11px] text-[#b9cacb] tracking-wider uppercase">
              LATENCY: 142ms | FAISS: ONLINE
            </span>
          </div>

          <button
            onClick={onLaunchAnalysis}
            className="relative inline-flex items-center justify-center px-4 py-2 rounded-lg bg-gradient-to-r from-[#00f2fe] to-[#0053db] text-xs font-semibold text-[#080e1a] shadow-[0_0_16px_rgba(0,242,254,0.35)] hover:shadow-[0_0_24px_rgba(0,242,254,0.55)] transition-all active:scale-[0.98] cursor-pointer"
          >
            Launch Case Analysis
          </button>

          <div
            title="Dr. Sarah Chen, Attending Physician"
            className="w-8 h-8 rounded-full bg-gradient-to-br from-[#e0fdff] to-[#00f2fe] flex items-center justify-center cursor-pointer border border-[#00f2fe]/40 shadow-sm"
          >
            <span className="material-symbols-outlined text-[#00373a] text-[18px]">person</span>
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="xl:hidden p-1.5 rounded-lg bg-[#161c28] border border-[#3a494b] text-[#dde2f3] hover:text-[#00f2fe]"
            aria-label="Toggle menu"
          >
            <span className="material-symbols-outlined text-[20px]">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="xl:hidden bg-[#080e1a]/95 border-b border-[#00f2fe]/20 px-4 py-3 flex flex-col gap-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id, item.href)}
              className={`text-left px-3 py-2 rounded-md text-sm transition-colors ${
                activeTab === item.id
                  ? 'bg-[#00f2fe] text-[#080e1a] font-semibold'
                  : 'text-[#b9cacb] hover:text-[#dde2f3]'
              }`}
            >
              {item.label}
            </button>
          ))}
          <div className="pt-2 border-t border-[#3a494b]/30 flex items-center justify-between text-[11px] font-mono text-[#b9cacb]">
            <span>LATENCY: 142ms</span>
            <span className="text-[#00f2fe]">FAISS: ONLINE</span>
          </div>
        </div>
      )}
    </header>
  );
};
