import React, { useState } from 'react';
import { Citation } from '@/lib/types';
import { BookOpen, CheckCircle, AlertCircle } from 'lucide-react';

interface Props {
  citation: Citation;
  index: number;
  onSelect: (citation: Citation) => void;
}

export const CitationMarker: React.FC<Props> = ({ citation, index, onSelect }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span className="relative inline-block mx-0.5 align-baseline">
      <button
        type="button"
        onClick={() => onSelect(citation)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-semibold rounded bg-blue-50 text-blue-700 hover:bg-blue-100 hover:text-blue-900 border border-blue-200 transition-colors cursor-pointer"
      >
        <BookOpen className="w-2.5 h-2.5" />
        <span>[{index + 1}]</span>
      </button>

      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-900 text-white rounded-lg shadow-xl text-xs z-50 pointer-events-none animate-in fade-in duration-100">
          <div className="flex items-center justify-between gap-1 mb-1 border-b border-slate-700 pb-1">
            <span className="font-semibold text-blue-300 truncate">
              {citation.document_filename || 'Source Document'}
            </span>
            {citation.page && (
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                p. {citation.page}
              </span>
            )}
          </div>
          {citation.quote && (
            <p className="italic text-slate-300 line-clamp-3 mt-1 text-[11px]">
              "{citation.quote}"
            </p>
          )}
          <div className="mt-2 pt-1 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              {citation.is_supported ? (
                <CheckCircle className="w-3 h-3 text-emerald-400" />
              ) : (
                <AlertCircle className="w-3 h-3 text-amber-400" />
              )}
              {citation.is_supported ? 'Verified quote' : 'Context reference'}
            </span>
            <span className="text-blue-400">Click to inspect</span>
          </div>
        </div>
      )}
    </span>
  );
};
