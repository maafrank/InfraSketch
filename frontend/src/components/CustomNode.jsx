import { Handle, Position } from 'reactflow';

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

export default function CustomNode({ data }) {
  const color = getNodeColor(data.type);

  return (
    <div
      className="custom-node"
      style={{
        background: color,
        borderColor: color,
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <div className="node-label">{data.label}</div>
        <div className="node-type-badge">{data.type}</div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
