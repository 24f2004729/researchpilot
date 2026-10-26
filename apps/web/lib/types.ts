export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  size_bytes: number;
  page_count: number;
  status: 'queued' | 'processing' | 'ready' | 'failed';
  error_code?: string | null;
  created_at: string;
}

export interface Citation {
  source_id: string;
  document_id?: string | null;
  document_filename?: string | null;
  page?: number | null;
  quote?: string | null;
  is_valid: boolean;
  is_supported: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status: 'completed' | 'failed' | 'streaming';
  model_name?: string | null;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  created_at: string;
  citations: Citation[];
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  messages: Message[];
}
