import React, { useState, useEffect, useRef } from 'react';
import { Conversation, Message, Citation, Document } from '@/lib/types';
import { MessageList } from './message-list';
import { MessageComposer } from './message-composer';
import { SourcePanel } from '../sources/source-panel';
import { api } from '@/lib/api-client';

interface Props {
  conversationId: string;
  activeDocuments: Document[];
  selectedDocIds: string[];
}

export const ChatPanel: React.FC<Props> = ({
  conversationId,
  activeDocuments,
  selectedDocIds,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingStage, setStreamingStage] = useState<string | null>(null);
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadConversation = async () => {
    try {
      const conv = await api.getConversation(conversationId);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    }
  };

  useEffect(() => {
    loadConversation();
  }, [conversationId]);

  const handleSendMessage = async (question: string) => {
    setIsLoading(true);
    setStreamingText('');
    setStreamingStage('verifying_documents');
    setStreamingCitations([]);

    // Add optimistic user message to list
    const userMsg: Message = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: question,
      status: 'completed',
      input_tokens: 0,
      output_tokens: 0,
      latency_ms: 0,
      created_at: new Date().toISOString(),
      citations: [],
    };
    setMessages((prev) => [...prev, userMsg]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulatedText = '';

    await api.streamQuestion(
      conversationId,
      question,
      selectedDocIds.length > 0 ? selectedDocIds : undefined,
      {
        onToken: (token) => {
          accumulatedText += token;
          setStreamingText(accumulatedText);
        },
        onCitations: (citations) => {
          setStreamingCitations(citations);
        },
        onStatus: (stage) => {
          setStreamingStage(stage);
        },
        onDone: (messageId) => {
          setIsLoading(false);
          setStreamingStage(null);
          setStreamingText('');
          // Refresh conversation from DB
          loadConversation();
        },
        onError: (err) => {
          setIsLoading(false);
          setStreamingStage(null);
          alert(`Error: ${err.message}`);
          loadConversation();
        },
      },
      controller.signal,
    );
  };

  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setStreamingStage(null);
  };

  return (
    <div className="flex-1 flex overflow-hidden relative">
      <div className="flex-1 flex flex-col bg-slate-50/50">
        <MessageList
          messages={messages}
          streamingText={streamingText}
          streamingStage={streamingStage}
          streamingCitations={streamingCitations}
          isStreaming={isLoading}
          onSelectCitation={(c) => setActiveCitation(c)}
        />

        <MessageComposer
          onSendMessage={handleSendMessage}
          onAbort={handleAbort}
          isLoading={isLoading}
          activeDocuments={activeDocuments.filter((d) => selectedDocIds.includes(d.id))}
        />
      </div>

      {activeCitation && (
        <SourcePanel
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </div>
  );
};
