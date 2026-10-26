import { auth } from './auth';
import { User, Workspace, Document, Conversation, Message, Citation } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string = 'ERROR', status: number = 400) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = auth.getToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) {
    return {} as T;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = data.error || {};
    const code = err.code || `HTTP_${res.status}`;
    const message = err.message || res.statusText || 'Request failed';
    if (res.status === 401 && typeof window !== 'undefined') {
      auth.clear();
      window.location.href = '/login';
    }
    throw new ApiError(message, code, res.status);
  }

  return data as T;
}

export const api = {
  // Authentication
  async register(email: string, password: string):Promise<{ access_token: string; user_id: string; email: string }> {
    return request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async login(email: string, password: string): Promise<{ access_token: string; user_id: string; email: string }> {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getMe(): Promise<User> {
    return request<User>('/auth/me');
  },

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    return request<Workspace[]>('/workspaces');
  },

  async createWorkspace(name: string): Promise<Workspace> {
    return request<Workspace>('/workspaces', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  // Documents
  async listDocuments(workspaceId: string): Promise<Document[]> {
    return request<Document[]>(`/workspaces/${workspaceId}/documents`);
  },

  async uploadDocument(workspaceId: string, file: File): Promise<{ document_id: string; status: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/workspaces/${workspaceId}/documents`, {
      method: 'POST',
      body: formData,
    });
  },

  async deleteDocument(documentId: string): Promise<void> {
    return request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  },

  async retryDocument(documentId: string): Promise<Document> {
    return request<Document>(`/documents/${documentId}/retry`, {
      method: 'POST',
    });
  },

  // Conversations
  async createConversation(workspaceId: string, title?: string): Promise<Conversation> {
    return request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, title }),
    });
  },

  async getConversation(conversationId: string): Promise<Conversation> {
    return request<Conversation>(`/conversations/${conversationId}`);
  },

  async askQuestion(
    conversationId: string,
    question: string,
    documentIds?: string[],
  ): Promise<Message> {
    return request<Message>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        question,
        document_ids: documentIds,
        stream: false,
      }),
    });
  },

  async streamQuestion(
    conversationId: string,
    question: string,
    documentIds: string[] | undefined,
    callbacks: {
      onToken: (token: string) => void;
      onCitations: (citations: Citation[], insufficientEvidence: boolean) => void;
      onStatus: (stage: string) => void;
      onDone: (messageId: string) => void;
      onError: (err: Error) => void;
    },
    abortSignal?: AbortSignal,
  ): Promise<void> {
    const token = auth.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question,
          document_ids: documentIds,
          stream: true,
        }),
        signal: abortSignal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(errorData.error?.message || 'Streaming failed', errorData.error?.code || 'STREAM_FAILED', response.status);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No readable stream available in response.');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;
          const lines = rawEvent.split('\n');
          let eventType = 'message';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6).trim();
            }
          }

          if (eventData) {
            try {
              const parsed = JSON.parse(eventData);
              if (eventType === 'token') {
                callbacks.onToken(parsed.text);
              } else if (eventType === 'citations') {
                callbacks.onCitations(parsed.citations || [], parsed.insufficient_evidence || false);
              } else if (eventType === 'status') {
                callbacks.onStatus(parsed.stage);
              } else if (eventType === 'done') {
                callbacks.onDone(parsed.message_id);
              } else if (eventType === 'error') {
                callbacks.onError(new Error(parsed.message || 'Stream error'));
              }
            } catch (err) {
              console.error('Failed to parse SSE payload:', eventData, err);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        callbacks.onError(err);
      }
    }
  },
};
