import React from 'react';
import { Document } from '@/lib/types';
import { ProcessingStatusBadge } from './processing-status';
import { Trash2, RotateCw, FileText, CheckSquare, Square } from 'lucide-react';
import { api } from '@/lib/api-client';

interface Props {
  documents: Document[];
  selectedDocIds: string[];
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onRefresh: () => void;
}

export const DocumentList: React.FC<Props> = ({
  documents,
  selectedDocIds,
  onToggleSelect,
  onSelectAll,
  onClearSelection,
  onRefresh,
}) => {
  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete '${filename}'? This will remove all extracted chunks and vectors.`)) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleRetry = async (docId: string) => {
    try {
      await api.retryDocument(docId);
      onRefresh();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    }
  };

  const allReadySelected =
    documents.filter((d) => d.status === 'ready').length > 0 &&
    documents
      .filter((d) => d.status === 'ready')
      .every((d) => selectedDocIds.includes(d.id));

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 px-4 bg-slate-50 rounded-xl border border-dashed border-slate-300">
        <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h4 className="text-sm font-semibold text-slate-700">No documents ingested yet</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Upload PDF, TXT, or Markdown documents to begin semantic search and evidence-grounded research synthesis.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={allReadySelected ? onClearSelection : onSelectAll}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1.5"
          >
            {allReadySelected ? (
              <CheckSquare className="w-4 h-4 text-blue-600" />
            ) : (
              <Square className="w-4 h-4 text-slate-400" />
            )}
            <span>Select All Ready ({selectedDocIds.length} active)</span>
          </button>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
        >
          <RotateCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div className="divide-y divide-slate-100">
        {documents.map((doc) => {
          const isSelected = selectedDocIds.includes(doc.id);
          const isReady = doc.status === 'ready';

          return (
            <div
              key={doc.id}
              className={`p-4 flex items-center justify-between hover:bg-slate-50/70 transition-colors ${
                isSelected ? 'bg-blue-50/30' : ''
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <button
                  type="button"
                  disabled={!isReady}
                  onClick={() => onToggleSelect(doc.id)}
                  className={`p-0.5 rounded transition-colors ${
                    !isReady
                      ? 'opacity-40 cursor-not-allowed'
                      : 'text-slate-400 hover:text-slate-600'
                  }`}
                >
                  {isSelected ? (
                    <CheckSquare className="w-4 h-4 text-blue-600" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-900 truncate">{doc.filename}</p>
                    <ProcessingStatusBadge status={doc.status} errorCode={doc.error_code} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                    <span>{(doc.size_bytes / 1024).toFixed(1)} KB</span>
                    {doc.page_count > 0 && <span>• {doc.page_count} pages</span>}
                    <span>• {new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                {doc.status === 'failed' && (
                  <button
                    type="button"
                    onClick={() => handleRetry(doc.id)}
                    title="Retry Ingestion"
                    className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <RotateCw className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  title="Delete Document"
                  className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
