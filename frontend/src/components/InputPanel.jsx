import { useState } from 'react';

export default function InputPanel({ onGenerate, loading }) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      onGenerate(prompt);
    }
  };

  return (
    <div className="input-panel">
      <h2>System Design Generator</h2>
      <form onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your system... (e.g., Build a scalable video streaming platform)"
          disabled={loading}
          rows={4}
        />
        <button type="submit" disabled={loading || !prompt.trim()}>
          {loading ? 'Generating...' : 'Generate System'}
        </button>
      </form>
    </div>
  );
}
