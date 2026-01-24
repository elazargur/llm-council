import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Login from './components/Login';
import { api } from './api';
import './App.css';

function App() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // Session state
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Model selection state
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedCouncilModels, setSelectedCouncilModels] = useState([]);
  const [selectedChairmanModel, setSelectedChairmanModel] = useState('');

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setAvailableModels(data.available_models);
      setSelectedCouncilModels(data.default_council_models);
      setSelectedChairmanModel(data.default_chairman_model);
    } catch (error) {
      console.error('Failed to load models:', error);
      if (error.message === 'Unauthorized') {
        api.clearAuth();
        setIsAuthenticated(false);
        setMessages([]);
      }
    }
  };

  const clearAuthState = () => {
    api.clearAuth();
    setIsAuthenticated(false);
    setMessages([]);
    setSessions([]);
    setCurrentSessionId(null);
  };

  const loadSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      if (error.message === 'Unauthorized') {
        clearAuthState();
      }
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const session = await api.getSession(sessionId);
      setCurrentSessionId(session.id);
      setMessages(session.messages || []);
    } catch (error) {
      console.error('Failed to load session:', error);
      if (error.message === 'Unauthorized') {
        clearAuthState();
      }
    }
  };

  // Check if already authenticated on mount
  useEffect(() => {
    const checkExistingAuth = async () => {
      if (api.hasStoredAuth()) {
        const isValid = await api.checkAuth();
        if (isValid) {
          setIsAuthenticated(true);
          loadModels();
          loadSessions();
        } else {
          api.clearAuth();
        }
      }
      setIsCheckingAuth(false);
    };
    checkExistingAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
    loadModels();
    loadSessions();
  };

  const handleLogout = () => {
    clearAuthState();
  };

  const handleNewConversation = async () => {
    try {
      const session = await api.createSession();
      setSessions((prev) => [
        { id: session.id, title: session.title, created_at: session.created_at, message_count: 0 },
        ...prev,
      ]);
      setCurrentSessionId(session.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create session:', error);
      if (error.message === 'Unauthorized') {
        clearAuthState();
      }
    }
  };

  const handleSelectConversation = async (sessionId) => {
    if (sessionId === currentSessionId) return;
    await loadSession(sessionId);
  };

  const handleDeleteConversation = async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      if (error.message === 'Unauthorized') {
        clearAuthState();
      }
    }
  };

  const handleSendMessage = async (content) => {
    // Create session if none exists
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const session = await api.createSession();
        sessionId = session.id;
        setSessions((prev) => [
          { id: session.id, title: session.title, created_at: session.created_at, message_count: 0 },
          ...prev,
        ]);
        setCurrentSessionId(sessionId);
      } catch (error) {
        console.error('Failed to create session:', error);
        return;
      }
    }

    setIsLoading(true);
    try {
      // Add user message to UI
      const userMessage = { role: 'user', content };
      setMessages((prev) => [...prev, userMessage]);

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
        modelStatus: {}, // Track per-model status: { model: 'pending' | 'success' | 'failed' }
      };

      // Add the partial assistant message
      setMessages((prev) => [...prev, assistantMessage]);

      // Run council with streaming
      const modelConfig = {
        councilModels: selectedCouncilModels,
        chairmanModel: selectedChairmanModel,
      };

      await api.runCouncilStream(content, modelConfig, sessionId, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              // Initialize all models as pending
              if (event.data?.models) {
                lastMsg.modelStatus = {};
                event.data.models.forEach((m) => {
                  lastMsg.modelStatus[m] = 'pending';
                });
              }
              return messages;
            });
            break;

          case 'model_status':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              if (event.data?.model) {
                lastMsg.modelStatus = {
                  ...lastMsg.modelStatus,
                  [event.data.model]: event.data.status,
                };
              }
              return messages;
            });
            break;

          case 'stage1_complete':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return messages;
            });
            break;

          case 'stage2_start':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              // Reset model status for stage 2
              if (event.data?.models) {
                lastMsg.modelStatus = {};
                event.data.models.forEach((m) => {
                  lastMsg.modelStatus[m] = 'pending';
                });
              }
              return messages;
            });
            break;

          case 'stage2_complete':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return messages;
            });
            break;

          case 'stage3_start':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              // Show chairman model as pending
              if (event.data?.model) {
                lastMsg.modelStatus = { [event.data.model]: 'pending' };
              }
              return messages;
            });
            break;

          case 'stage3_complete':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return messages;
            });
            break;

          case 'complete':
            setIsLoading(false);
            // Refresh sessions to get updated title
            loadSessions();
            break;

          case 'error':
            console.error('Stream error:', event.message || event.data?.message);
            setIsLoading(false);
            // Show error to user
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.error = event.message || event.data?.message || 'Unknown error';
              lastMsg.loading = { stage1: false, stage2: false, stage3: false };
              return messages;
            });
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      if (error.message === 'Unauthorized') {
        clearAuthState();
        return;
      }
      // Remove optimistic messages on error
      setMessages((prev) => prev.slice(0, -2));
      setIsLoading(false);
    }
  };

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div className="app loading-screen">
        <div>Loading...</div>
      </div>
    );
  }

  // Show login if not authenticated
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // Create a conversation object for ChatInterface compatibility
  const currentConversation = {
    id: currentSessionId || 'new',
    messages: messages,
  };

  return (
    <div className="app">
      <Sidebar
        conversations={sessions}
        currentConversationId={currentSessionId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        availableModels={availableModels}
        selectedCouncilModels={selectedCouncilModels}
        selectedChairmanModel={selectedChairmanModel}
        onCouncilModelsChange={setSelectedCouncilModels}
        onChairmanModelChange={setSelectedChairmanModel}
        onLogout={handleLogout}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  );
}

export default App;
