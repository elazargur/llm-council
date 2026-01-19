import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const WelcomeGuide = () => (
    <div className="empty-state">
      <h2>Welcome to LLM Council</h2>
      <p className="subtitle">A deliberation system where multiple AI models collaborate to answer your question</p>

      <div className="guide-section">
        <h3>How it works</h3>
        <div className="stages-overview">
          <div className="stage-item">
            <span className="stage-number">1</span>
            <span>Each model answers independently (with web access)</span>
          </div>
          <div className="stage-item">
            <span className="stage-number">2</span>
            <span>Models anonymously rank each other's responses</span>
          </div>
          <div className="stage-item">
            <span className="stage-number">3</span>
            <span>Chairman synthesizes the best final answer</span>
          </div>
        </div>
      </div>

      <div className="guide-section">
        <h3>Best practices</h3>
        <ul className="tips-list">
          <li><strong>One question per session</strong> — This isn't a chat. Include all context upfront.</li>
          <li><strong>Be specific</strong> — "Compare React vs Vue for a small team" beats "What frontend framework?"</li>
          <li><strong>Ask complex questions</strong> — The council shines on nuanced topics with multiple valid perspectives.</li>
        </ul>
      </div>

      <div className="guide-section">
        <h3>Great questions for the council</h3>
        <ul className="examples-list">
          <li>"What are the tradeoffs between microservices and monolith for a 5-person startup?"</li>
          <li>"Analyze the latest developments in [topic] and summarize key takeaways"</li>
          <li>"I'm deciding between X and Y for [use case]. What should I consider?"</li>
        </ul>
      </div>
    </div>
  );

  if (!conversation) {
    return (
      <div className="chat-interface">
        <WelcomeGuide />
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <WelcomeGuide />
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content" dir="auto">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            dir="auto"
            placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
