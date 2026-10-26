import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

interface Props {
  status: 'queued' | 'processing' | 'ready' | 'failed';
  errorCode?: string | null;
}

export const ProcessingStatusBadge: React.FC<Props> = ({ status, errorCode }) => {
  switch (status) {
    case 'ready':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          Ready
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin" />
          Processing
        </span>
      );
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
          <Clock className="w-3.5 h-3.5 text-blue-600" />
          Queued
        </span>
      );
    case 'failed':
      return (
        <span
          title={errorCode || 'Ingestion failed'}
          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200 cursor-help"
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
          Failed
        </span>
      );
    default:
      return null;
  }
};
