import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, FileText, Sparkles } from 'lucide-react';
import { Document } from '@/lib/types';

interface Props {
  onSendMessage: (question: string) => void;
  onAbort: () => void;
  isLoading: boolean;
  activeDocuments: Document[];
}

export const MessageComposer: React.FC<Props> = ({
  onSendMessage,
  onAbort,
  isLoading,
  activeDocuments,
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isLoading) {
      textareaRef.current?.focus();
    }
  }, [isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="p-4 border-t border-slate-200 bg-white">
      {/* Active Document Filters */}
      <div className="flex items-center gap-1.5 mb-2 overflow-x-auto text-xs pb-1">
        <span className="text-slate-400 font-medium flex items-center gap-1 flex-shrink-0">
          <FileText className="w-3.5 h-3.5" />
          Active Context:
        </span>
        {activeDocuments.length === 0 ? (
          <span className="text-amber-600 font-medium">All ready workspace documents</span>
        ) : (
          activeDocuments.map((doc) => (
            <span
              key={doc.id}
              className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium truncate max-w-[180px]"
            >
              {doc.filename}
            </span>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question across selected research documents..."
          rows={2}
          className="w-full resize-none rounded-xl border border-slate-300 p-3 pr-24 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
        />

        <div className="absolute right-2 bottom-3 flex items-center gap-1.5">
          {isLoading ? (
            <button
              type="button"
              onClick={onAbort}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-200 text-xs font-semibold transition-colors"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="inline-flex items-center justify-center p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </form>
      <p className="text-[11px] text-slate-400 text-center mt-2">
        Evidence-grounded synthesis with strict citation validation. Unanswerable queries will trigger honest abstention.
      </p>
    </div>
  );
};
