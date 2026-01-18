import './Sidebar.css';
import ModelSelector from './ModelSelector';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  availableModels,
  selectedCouncilModels,
  selectedChairmanModel,
  onCouncilModelsChange,
  onChairmanModelChange,
  onLogout,
}) {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const handleDelete = (e, sessionId) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation?')) {
      onDeleteConversation(sessionId);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
      </div>

      {availableModels.length > 0 && (
        <ModelSelector
          availableModels={availableModels}
          selectedCouncilModels={selectedCouncilModels}
          selectedChairmanModel={selectedChairmanModel}
          onCouncilModelsChange={onCouncilModelsChange}
          onChairmanModelChange={onChairmanModelChange}
        />
      )}

      <div className="sidebar-actions">
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-meta">
                <span>{formatDate(conv.created_at)}</span>
                <span style={{ marginLeft: '8px' }}>{conv.message_count} messages</span>
                <button
                  className="delete-btn"
                  onClick={(e) => handleDelete(e, conv.id)}
                  title="Delete conversation"
                >
                  ×
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="sidebar-footer">
        <button className="logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      </div>
    </div>
  );
}
