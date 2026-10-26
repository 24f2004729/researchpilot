'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api-client';
import { auth } from '@/lib/auth';
import { Workspace, User } from '@/lib/types';
import { BookOpen, Plus, FolderKanban, LogOut, ArrowRight, Loader2, Sparkles } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  useEffect(() => {
    if (!auth.isAuthenticated()) {
      router.push('/login');
      return;
    }

    const init = async () => {
      try {
        const u = await api.getMe();
        setUser(u);
        const wsList = await api.listWorkspaces();
        setWorkspaces(wsList);
      } catch (err) {
        auth.clear();
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [router]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setCreateLoading(true);
    try {
      const created = await api.createWorkspace(newWorkspaceName.trim());
      setWorkspaces((prev) => [...prev, created]);
      setNewWorkspaceName('');
      setIsCreating(false);
      router.push(`/workspaces/${created.id}`);
    } catch (err: any) {
      alert(`Failed to create workspace: ${err.message}`);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleLogout = () => {
    auth.clear();
    router.push('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Loading research workspaces...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between sticky top-0 z-30 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold shadow-sm">
            <BookOpen className="w-4 h-4" />
          </div>
          <span className="font-bold text-slate-900 tracking-tight text-lg">ResearchPilot</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs font-semibold text-slate-800">{user?.email}</p>
            <p className="text-[10px] text-slate-400">Authenticated Session</p>
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Your Workspaces</h2>
            <p className="text-sm text-slate-500 mt-1">
              Select or create an isolated workspace for your research literature and documents.
            </p>
          </div>

          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Workspace</span>
          </button>
        </div>

        {/* Create Modal */}
        {isCreating && (
          <div className="mb-8 p-6 bg-white border border-blue-200 rounded-2xl shadow-lg animate-in fade-in duration-150">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Create New Research Workspace</h3>
            <form onSubmit={handleCreateWorkspace} className="flex gap-3">
              <input
                type="text"
                required
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder="e.g. Distributed Consensus Papers"
                className="flex-1 px-4 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={createLoading || !newWorkspaceName.trim()}
                className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl transition-colors shadow-sm inline-flex items-center gap-2"
              >
                {createLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>Create</span>
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                Cancel
              </button>
            </form>
          </div>
        )}

        {/* Workspaces Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workspaces.map((ws) => (
            <div
              key={ws.id}
              onClick={() => router.push(`/workspaces/${ws.id}`)}
              className="group bg-white border border-slate-200 hover:border-blue-500/50 hover:shadow-md rounded-2xl p-6 transition-all duration-150 cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
                  <FolderKanban className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-slate-900 text-base group-hover:text-blue-600 transition-colors">
                  {ws.name}
                </h3>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  ID: {ws.id.slice(0, 8)}...
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Created {new Date(ws.created_at).toLocaleDateString()}</span>
                <span className="inline-flex items-center gap-1 font-medium text-blue-600 group-hover:translate-x-0.5 transition-transform">
                  Open Workspace <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
