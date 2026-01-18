import './Sidebar.css';
import ModelSelector from './ModelSelector';

export default function Sidebar({
  onNewConversation,
  availableModels,
  selectedCouncilModels,
  selectedChairmanModel,
  onCouncilModelsChange,
  onChairmanModelChange,
  onLogout,
}) {
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

      <div className="sidebar-footer">
        <button className="logout-btn" onClick={onLogout}>
          Sign Out
        </button>
      </div>
    </div>
  );
}
