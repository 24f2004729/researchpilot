import React from 'react';
import { Citation } from '@/lib/types';
import { X, FileText, CheckCircle2, AlertTriangle, ExternalLink, Hash } from 'lucide-react';

interface Props {
  citation: Citation | null;
  onClose: () => void;
}

export const SourcePanel: React.FC<Props> = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="w-96 border-l border-slate-200 bg-white flex flex-col h-full shadow-lg z-20 animate-in slide-in-from-right duration-200">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <h3 className="font-semibold text-slate-900 text-sm">Citation Inspector</h3>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-200/50 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Document Header */}
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Source Document
          </span>
          <p className="text-sm font-semibold text-slate-900 mt-0.5 truncate">
            {citation.document_filename || 'Unknown Document'}
          </p>
          <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
            {citation.page && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-medium border border-blue-200">
                Page {citation.page}
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-slate-400 font-mono text-[11px]">
              <Hash className="w-3 h-3" />
              {citation.source_id.slice(0, 8)}...
            </span>
          </div>
        </div>

        {/* Verification Status */}
        <div className="space-y-2">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Grounding Verification
          </span>
          <div className="p-3 rounded-lg border bg-white flex items-start gap-2.5">
            {citation.is_valid ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className="text-xs font-semibold text-slate-800">
                {citation.is_valid ? 'Valid Context Passage' : 'Unverified Reference'}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {citation.is_valid
                  ? 'This passage was retrieved directly from authorized workspace storage and supplied to the model context.'
                  : 'This citation could not be mapped to a chunk present in the retrieved context.'}
              </p>
            </div>
          </div>

          <div className="p-3 rounded-lg border bg-white flex items-start gap-2.5">
            {citation.is_supported ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className="text-xs font-semibold text-slate-800">
                {citation.is_supported ? 'Verbatim Quote Support' : 'Semantic Reference'}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {citation.is_supported
                  ? 'Supporting quote was verified against raw extracted document text.'
                  : 'Cited claim is grounded in the broader passage context.'}
              </p>
            </div>
          </div>
        </div>

        {/* Supporting Quote */}
        {citation.quote && (
          <div>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Exact Supporting Excerpt
            </span>
            <blockquote className="mt-1.5 p-3 bg-amber-50/70 border-l-4 border-amber-400 rounded-r-lg text-xs italic text-slate-800 leading-relaxed">
              "{citation.quote}"
            </blockquote>
          </div>
        )}
      </div>
    </div>
  );
};
