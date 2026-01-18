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

  // Conversation state (in-memory only, no persistence)
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

  // Check if already authenticated on mount
  useEffect(() => {
    const checkExistingAuth = async () => {
      if (api.hasStoredAuth()) {
        const isValid = await api.checkAuth();
        if (isValid) {
          setIsAuthenticated(true);
          loadModels();
        } else {
          api.clearAuth();
        }
      }
      setIsCheckingAuth(false);
    };
    checkExistingAuth();
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
    loadModels();
  };

  const handleLogout = () => {
    api.clearAuth();
    setIsAuthenticated(false);
    setMessages([]);
  };

  const handleNewConversation = () => {
    setMessages([]);
  };

  const handleSendMessage = async (content) => {
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
      };

      // Add the partial assistant message
      setMessages((prev) => [...prev, assistantMessage]);

      // Run council with streaming
      const modelConfig = {
        councilModels: selectedCouncilModels,
        chairmanModel: selectedChairmanModel,
      };

      await api.runCouncilStream(content, modelConfig, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setMessages((prev) => {
              const messages = [...prev];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
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
            break;

          case 'error':
            console.error('Stream error:', event.message || event.data?.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      if (error.message === 'Unauthorized') {
        handleLogout();
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
    id: 'session',
    messages: messages,
  };

  return (
    <div className="app">
      <Sidebar
        conversations={[]}
        currentConversationId="session"
        onSelectConversation={() => {}}
        onNewConversation={handleNewConversation}
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
