import { Handle, Position } from 'reactflow';
import { useState } from 'react';

export default function CustomNode({ data, id }) {
  const [isHovered, setIsHovered] = useState(false);

  const handleDelete = (e) => {
    e.stopPropagation();
    if (data.onDelete) {
      data.onDelete(id);
    }
  };

  return (
    <div
      className={`custom-node node-type-${data.type}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type-badge">{data.type}</div>
      </div>
      <Handle type="source" position={Position.Bottom} />

      {isHovered && (
        <button
          className="node-delete-button"
          onClick={handleDelete}
          title="Delete node"
        >
          🗑️
        </button>
      )}
    </div>
  );
}
