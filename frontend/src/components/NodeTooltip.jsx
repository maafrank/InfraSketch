import { useState } from 'react';

export default function NodeTooltip({ node, onSave }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({
    label: node.data.label,
    description: node.data.description,
    technology: node.data.metadata?.technology || '',
    inputs: node.data.inputs?.join(', ') || '',
    outputs: node.data.outputs?.join(', ') || '',
  });

  if (!node) return null;

  const handleSave = () => {
    // Convert comma-separated strings back to arrays
    const updatedNode = {
      id: node.id,
      type: node.data.type,
      label: editedData.label,
      description: editedData.description,
      inputs: editedData.inputs.split(',').map(s => s.trim()).filter(s => s),
      outputs: editedData.outputs.split(',').map(s => s.trim()).filter(s => s),
      metadata: {
        ...node.data.metadata,
        technology: editedData.technology,
      },
      position: node.position,
    };

    onSave(updatedNode);
    setIsEditing(false);
  };

  const handleCancel = () => {
    // Reset to original values
    setEditedData({
      label: node.data.label,
      description: node.data.description,
      technology: node.data.metadata?.technology || '',
      inputs: node.data.inputs?.join(', ') || '',
      outputs: node.data.outputs?.join(', ') || '',
    });
    setIsEditing(false);
  };

  return (
    <div className="node-tooltip">
      <div className="tooltip-header">
        {!isEditing ? (
          <>
            <h4>{node.data.label}</h4>
            <button
              className="tooltip-edit-btn"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
              title="Edit node"
            >
              ✏️
            </button>
          </>
        ) : (
          <input
            type="text"
            value={editedData.label}
            onChange={(e) => setEditedData({ ...editedData, label: e.target.value })}
            className="tooltip-input"
            placeholder="Node name"
          />
        )}
      </div>

      <p className="node-type">{node.data.type}</p>

      {!isEditing ? (
        <>
          <p className="node-description">{node.data.description}</p>

          {node.data.metadata?.technology && (
            <p className="node-tech">
              <strong>Technology:</strong> {node.data.metadata.technology}
            </p>
          )}

          {node.data.inputs && node.data.inputs.length > 0 && (
            <div className="node-io">
              <strong>Inputs:</strong> {node.data.inputs.join(', ')}
            </div>
          )}

          {node.data.outputs && node.data.outputs.length > 0 && (
            <div className="node-io">
              <strong>Outputs:</strong> {node.data.outputs.join(', ')}
            </div>
          )}
        </>
      ) : (
        <>
          <textarea
            value={editedData.description}
            onChange={(e) => setEditedData({ ...editedData, description: e.target.value })}
            className="tooltip-textarea"
            placeholder="Description"
            rows={3}
          />

          <input
            type="text"
            value={editedData.technology}
            onChange={(e) => setEditedData({ ...editedData, technology: e.target.value })}
            className="tooltip-input"
            placeholder="Technology"
          />

          <input
            type="text"
            value={editedData.inputs}
            onChange={(e) => setEditedData({ ...editedData, inputs: e.target.value })}
            className="tooltip-input"
            placeholder="Inputs (comma separated)"
          />

          <input
            type="text"
            value={editedData.outputs}
            onChange={(e) => setEditedData({ ...editedData, outputs: e.target.value })}
            className="tooltip-input"
            placeholder="Outputs (comma separated)"
          />

          <div className="tooltip-actions">
            <button className="tooltip-save-btn" onClick={handleSave}>
              Save
            </button>
            <button className="tooltip-cancel-btn" onClick={handleCancel}>
              Cancel
            </button>
          </div>
        </>
      )}

      {!isEditing && <p className="tooltip-hint">Click to chat about this component</p>}
    </div>
  );
}
