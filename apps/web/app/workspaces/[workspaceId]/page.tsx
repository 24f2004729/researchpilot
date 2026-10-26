'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api-client';
import { auth } from '@/lib/auth';
import { Document, Workspace, Conversation } from '@/lib/types';
import { DocumentList } from '@/components/documents/document-list';
import { UploadDialog } from '@/components/documents/upload-dialog';
import { ChatPanel } from '@/components/chat/chat-panel';
import {
  BookOpen,
  Upload,
  ArrowLeft,
  MessageSquare,
  Plus,
  Loader2,
  FileText,
  Shield,
  Layers,
} from 'lucide-react';

export default function WorkspaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchWorkspaceData = useCallback(async () => {
    try {
      const docs = await api.listDocuments(workspaceId);
      setDocuments(docs);

      // Auto-select ready documents initially if none selected
      setSelectedDocIds((prev) => {
        if (prev.length === 0) {
          return docs.filter((d) => d.status === 'ready').map((d) => d.id);
        }
        return prev;
      });
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login');
      return;
    }

    const init = async () => {
      try {
        const wsList = await api.listWorkspaces();
        const current = wsList.find((w) => w.id === workspaceId);
        if (!current) {
          router.push('/dashboard');
          return;
        }
        setWorkspace(current);

        // Fetch documents
        await fetchWorkspaceData();

        // Create default conversation if none exists
        const conv = await api.createConversation(workspaceId, 'Initial Research Session');
        setCurrentConversationId(conv.id);
        setConversations([conv]);
      } catch (err) {
        console.error('Workspace load error:', err);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [workspaceId, router, fetchWorkspaceData]);

  // Polling for processing documents
  useEffect(() => {
    const hasPending = documents.some((d) => d.status === 'queued' || d.status === 'processing');
    if (!hasPending) return;

    const interval = setInterval(() => {
      fetchWorkspaceData();
    }, 2500);

    return () => clearInterval(interval);
  }, [documents, fetchWorkspaceData]);

  const handleToggleSelect = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    setSelectedDocIds(documents.filter((d) => d.status === 'ready').map((d) => d.id));
  };

  const handleClearSelection = () => {
    setSelectedDocIds([]);
  };

  const handleNewConversation = async () => {
    try {
      const conv = await api.createConversation(
        workspaceId,
        `Research Session ${conversations.length + 1}`
      );
      setConversations((prev) => [conv, ...prev]);
      setCurrentConversationId(conv.id);
    } catch (err: any) {
      alert(`Could not create session: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Top Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between z-10 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-900 text-sm">{workspace?.name}</h2>
              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">
                {documents.filter((d) => d.status === 'ready').length} ready
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Tenant ID: {workspaceId.slice(0, 8)}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Document</span>
          </button>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Drawer: Documents & History */}
        <aside className="w-80 border-r border-slate-200 bg-white flex flex-col overflow-hidden flex-shrink-0">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              Corpus Documents
            </span>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              + Upload
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            <DocumentList
              documents={documents}
              selectedDocIds={selectedDocIds}
              onToggleSelect={handleToggleSelect}
              onSelectAll={handleSelectAll}
              onClearSelection={handleClearSelection}
              onRefresh={fetchWorkspaceData}
            />
          </div>

          {/* Sessions Footer */}
          <div className="p-3 border-t border-slate-200 bg-slate-50/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">Sessions</span>
              <button
                onClick={handleNewConversation}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                New
              </button>
            </div>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCurrentConversationId(c.id)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs truncate flex items-center gap-2 transition-colors ${
                    currentConversationId === c.id
                      ? 'bg-blue-50 text-blue-700 font-medium border border-blue-200'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate">{c.title}</span>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Center & Right: Research Chat Panel with Citations Inspector */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {currentConversationId ? (
            <ChatPanel
              key={currentConversationId}
              conversationId={currentConversationId}
              activeDocuments={documents}
              selectedDocIds={selectedDocIds}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-sm text-slate-400">Select or create a research session to begin.</p>
            </div>
          )}
        </main>
      </div>

      {/* Upload Dialog Modal */}
      <UploadDialog
        workspaceId={workspaceId}
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={fetchWorkspaceData}
      />
    </div>
  );
}
