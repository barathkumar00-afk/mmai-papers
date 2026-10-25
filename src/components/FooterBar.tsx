import React from 'react';

export const FooterBar: React.FC = () => {
  return (
    <aside className="fixed bottom-0 left-0 right-0 z-40 w-full h-8 bg-[#080e1a]/95 backdrop-blur-md border-t border-[#00f2fe]/20 flex items-center justify-center px-4">
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[14px] text-[#00f2fe]">verified_user</span>
        <p className="font-mono text-[11px] text-[#b9cacb] tracking-wider text-center truncate">
          AI-assisted clinical decision support — Not an autonomous diagnosis or substitute for professional medical judgment. Demo research prototype.
        </p>
      </div>
    </aside>
  );
};
