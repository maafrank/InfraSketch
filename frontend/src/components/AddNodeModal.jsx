import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import './AddNodeModal.css';

const NODE_TYPES = [
  { value: 'api', label: 'API' },
  { value: 'database', label: 'Database' },
  { value: 'cache', label: 'Cache' },
  { value: 'server', label: 'Server' },
  { value: 'loadbalancer', label: 'Load Balancer' },
  { value: 'queue', label: 'Queue' },
  { value: 'cdn', label: 'CDN' },
  { value: 'gateway', label: 'Gateway' },
  { value: 'storage', label: 'Storage' },
  { value: 'service', label: 'Service' },
];

export default function AddNodeModal({ isOpen, onClose, onAdd, preSelectedType = null, prefillData = null }) {
  const [formData, setFormData] = useState({
    type: preSelectedType || 'api',
    label: '',
    description: '',
    technology: '',
    notes: '',
  });

  // Update type when preSelectedType changes
  useEffect(() => {
    if (preSelectedType) {
      setFormData((prev) => ({ ...prev, type: preSelectedType }));
    }
  }, [preSelectedType]);

  // Prefill form data when provided (e.g., from tutorial)
  useEffect(() => {
    if (prefillData && isOpen) {
      setFormData({
        type: prefillData.type || 'api',
        label: prefillData.label || '',
        description: prefillData.description || '',
        technology: prefillData.metadata?.technology || '',
        notes: prefillData.metadata?.notes || '',
      });
    }
  }, [prefillData, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.label.trim()) {
      alert('Please enter a node label');
      return;
    }

    // Generate a readable ID from the label
    const baseId = formData.label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');

    // Add timestamp suffix to ensure uniqueness
    const nodeId = `${baseId}-${Date.now()}`;

    const node = {
      id: nodeId,
      type: formData.type,
      label: formData.label,
      description: formData.description || '',
      inputs: [],
      outputs: [],
      metadata: {
        technology: formData.technology || null,
        notes: formData.notes || null,
      },
      position: {
        x: Math.random() * 500 + 100,
        y: Math.random() * 300 + 100,
      },
    };

    onAdd(node);
    handleClose();
  };

  const handleClose = () => {
    setFormData({
      type: 'api',
      label: '',
      description: '',
      technology: '',
      notes: '',
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Add New Node</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="type">Type *</label>
            <select
              id="type"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              required
            >
              {NODE_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="label">Label *</label>
            <input
              id="label"
              type="text"
              value={formData.label}
              onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              placeholder="e.g., User Service"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="What does this component do?"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="technology">Technology</label>
            <input
              id="technology"
              type="text"
              value={formData.technology}
              onChange={(e) => setFormData({ ...formData, technology: e.target.value })}
              placeholder="e.g., Node.js, PostgreSQL"
            />
          </div>

          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Additional notes..."
              rows={2}
            />
          </div>

          <div className="modal-buttons">
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" variant="default">
              Add Node
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
