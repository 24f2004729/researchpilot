import React from 'react';
import { Message, Citation } from '@/lib/types';
import { CitationMarker } from './citation-marker';
import { Bot, User, AlertCircle, Cpu, Clock, Layers } from 'lucide-react';

interface Props {
  messages: Message[];
  streamingText: string;
  streamingStage: string | null;
  streamingCitations: Citation[];
  isStreaming: boolean;
  onSelectCitation: (citation: Citation) => void;
}

export const MessageList: React.FC<Props> = ({
  messages,
  streamingText,
  streamingStage,
  streamingCitations,
  isStreaming,
  onSelectCitation,
}) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      {messages.length === 0 && !isStreaming && (
        <div className="text-center py-16 px-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3 shadow-sm border border-blue-100">
            <Bot className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-800">Research Assistant Ready</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            Ask any research question across your selected documents. Every answer will be synthesized strictly from retrieved passages and backed with verifiable citations.
          </p>
        </div>
      )}

      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex gap-3 max-w-3xl ${
            msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-700 border border-slate-200'
            }`}
          >
            {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-blue-600" />}
          </div>

          <div
            className={`rounded-2xl p-4 shadow-sm text-sm ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-tr-none'
                : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
            }`}
          >
            <div className="leading-relaxed whitespace-pre-wrap">{msg.content}</div>

            {/* Citations Footer for Assistant Messages */}
            {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Grounding Citations ({msg.citations.length})
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {msg.citations.map((c, idx) => (
                    <CitationMarker
                      key={`${c.source_id}_${idx}`}
                      citation={c}
                      index={idx}
                      onSelect={onSelectCitation}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Metadata Footer */}
            {msg.role === 'assistant' && (
              <div className="mt-3 pt-2 border-t border-slate-50 flex items-center gap-3 text-[10px] text-slate-400">
                {msg.latency_ms > 0 && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {msg.latency_ms}ms
                  </span>
                )}
                {msg.model_name && (
                  <span className="flex items-center gap-1 font-mono">
                    <Cpu className="w-3 h-3" />
                    {msg.model_name}
                  </span>
                )}
                {msg.input_tokens > 0 && (
                  <span className="flex items-center gap-1">
                    <Layers className="w-3 h-3" />
                    {msg.input_tokens + msg.output_tokens} tokens
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Streaming Response Turn */}
      {isStreaming && (
        <div className="flex gap-3 max-w-3xl">
          <div className="w-8 h-8 rounded-full bg-slate-100 text-blue-600 border border-slate-200 flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 animate-pulse" />
          </div>

          <div className="rounded-2xl rounded-tl-none p-4 bg-white border border-slate-200 text-slate-800 shadow-sm text-sm space-y-3">
            {streamingStage && !streamingText && (
              <div className="flex items-center gap-2 text-xs text-blue-600 animate-pulse font-medium">
                <div className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                <span>
                  {streamingStage === 'verifying_documents'
                    ? 'Verifying workspace document access...'
                    : streamingStage === 'retrieving'
                    ? 'Retrieving hybrid candidates & rank fusion...'
                    : 'Generating grounded answer...'}
                </span>
              </div>
            )}

            {streamingText && (
              <div className="leading-relaxed whitespace-pre-wrap">{streamingText}</div>
            )}

            {streamingCitations.length > 0 && (
              <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-1.5">
                {streamingCitations.map((c, idx) => (
                  <CitationMarker
                    key={`stream_cit_${idx}`}
                    citation={c}
                    index={idx}
                    onSelect={onSelectCitation}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
