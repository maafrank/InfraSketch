export default function NodeTooltip({ node }) {
  if (!node) return null;

  return (
    <div className="node-tooltip">
      <h4>{node.data.label}</h4>
      <p className="node-type">{node.data.type}</p>
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

      <p className="tooltip-hint">Click to chat about this component</p>
    </div>
  );
}
