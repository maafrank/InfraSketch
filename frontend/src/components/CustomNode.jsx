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

  const handleToggleCollapse = (e) => {
    e.stopPropagation();
    if (data.onToggleCollapse) {
      data.onToggleCollapse(id);
    }
  };

  const handleRegroup = (e) => {
    e.stopPropagation();
    if (data.parent_id && data.onToggleCollapse) {
      // Collapse the parent group
      data.onToggleCollapse(data.parent_id);
    }
  };

  const isGroup = data.is_group;
  const isCollapsed = data.is_collapsed;
  const childCount = data.child_ids?.length || 0;
  const isDropTarget = data.isDropTarget;
  const hasParent = !!data.parent_id;

  // Determine classes
  const nodeClasses = [
    'custom-node',
    `node-type-${data.type}`,
    isGroup ? 'node-group' : '',
    isDropTarget ? 'drop-target' : '',
  ].filter(Boolean).join(' ');

  // Apply blended color for mixed-type groups
  const nodeStyle = {};
  if (data.blendedColor) {
    nodeStyle.backgroundColor = data.blendedColor;
    nodeStyle.opacity = '0.85'; // Slightly transparent to distinguish from regular nodes
  }

  return (
    <div
      className={nodeClasses}
      style={nodeStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Handle type="target" position={Position.Top} />

      {isGroup && (
        <div className="group-header">
          <button
            className="collapse-toggle"
            onClick={handleToggleCollapse}
            title={isCollapsed ? "Expand group" : "Collapse group"}
          >
            {isCollapsed ? '▶' : '▼'}
          </button>
          <span className="child-count">{childCount} node{childCount !== 1 ? 's' : ''}</span>
        </div>
      )}

      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type-badge">{data.type}</div>
      </div>
      <Handle type="source" position={Position.Bottom} />

      {hasParent && isHovered && (
        <button
          className="regroup-button"
          onClick={handleRegroup}
          title="Collapse group"
        >
          ▼
        </button>
      )}

      {isHovered && (
        <button
          className="node-delete-button"
          onClick={handleDelete}
          title="Delete node"
        >
          ×
        </button>
      )}

      {isDropTarget && (
        <div className="drop-hint">Drop to merge</div>
      )}
    </div>
  );
}
