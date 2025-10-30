import { Handle, Position } from 'reactflow';
import { useState } from 'react';

const getNodeColor = (type) => {
  const colors = {
    database: '#4A90E2',
    cache: '#F5A623',
    server: '#7ED321',
    api: '#BD10E0',
    loadbalancer: '#50E3C2',
    queue: '#D0021B',
    cdn: '#9013FE',
    gateway: '#417505',
    storage: '#B8E986',
    service: '#8B572A',
  };
  return colors[type] || '#888';
};

export default function CustomNode({ data, id }) {
  const [isHovered, setIsHovered] = useState(false);
  const color = getNodeColor(data.type);

  const handleDelete = (e) => {
    e.stopPropagation();
    if (data.onDelete) {
      data.onDelete(id);
    }
  };

  return (
    <div
      className="custom-node"
      style={{
        background: color,
        borderColor: color,
      }}
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
