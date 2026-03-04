import { useState } from 'react';
import LoadingAnimation from './LoadingAnimation';
import { Button } from '@/components/ui/button';
import { DEFAULT_MODEL, MODEL_OPTIONS } from '../constants/models';

export default function InputPanel({ onGenerate, loading }) {
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState(DEFAULT_MODEL);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      onGenerate(prompt, model);
    }
  };

  if (loading) {
    return <LoadingAnimation />;
  }

  return (
    <div className="input-panel">
      <h2>System Design Generator</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="model-select" style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
            AI Model:
          </label>
          <select
            id="model-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={loading}
            style={{
              padding: '8px 12px',
              fontSize: '14px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              backgroundColor: 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              width: '100%',
              maxWidth: '400px'
            }}
          >
            {MODEL_OPTIONS.map(opt => (
              <option key={opt.id} value={opt.id}>{opt.label} ({opt.description})</option>
            ))}
          </select>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your system... (e.g., Build a scalable video streaming platform)"
          disabled={loading}
          rows={4}
        />
        <Button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? 'Generating...' : 'Generate System'}
        </Button>
      </form>
    </div>
  );
}
