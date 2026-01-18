import { useState } from 'react';
import './ModelSelector.css';

export default function ModelSelector({
  availableModels,
  selectedCouncilModels,
  selectedChairmanModel,
  onCouncilModelsChange,
  onChairmanModelChange,
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleCouncilToggle = (model) => {
    if (selectedCouncilModels.includes(model)) {
      onCouncilModelsChange(selectedCouncilModels.filter((m) => m !== model));
    } else {
      onCouncilModelsChange([...selectedCouncilModels, model]);
    }
  };

  const getModelDisplayName = (model) => {
    // Extract just the model name from the full path (e.g., "openai/gpt-4o" -> "gpt-4o")
    return model.split('/')[1] || model;
  };

  return (
    <div className="model-selector">
      <div
        className="model-selector-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="model-selector-toggle">{isExpanded ? '▼' : '▶'}</span>
        <span className="model-selector-title">
          Models ({selectedCouncilModels.length} selected)
        </span>
      </div>

      {isExpanded && (
        <div className="model-selector-content">
          <div className="model-section">
            <div className="model-section-label">Council Members:</div>
            <div className="model-checkboxes">
              {availableModels.map((model) => (
                <label key={model} className="model-checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedCouncilModels.includes(model)}
                    onChange={() => handleCouncilToggle(model)}
                  />
                  <span className="model-name">{getModelDisplayName(model)}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="model-section">
            <div className="model-section-label">Chairman:</div>
            <select
              className="chairman-select"
              value={selectedChairmanModel}
              onChange={(e) => onChairmanModelChange(e.target.value)}
            >
              {availableModels.map((model) => (
                <option key={model} value={model}>
                  {getModelDisplayName(model)}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
