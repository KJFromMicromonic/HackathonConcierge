import { useState, useEffect, useRef } from 'react';
import { API_BASE } from '../lib/supabase';

interface ChatModel {
  id: string;
  provider: string;
  model: string;
  label: string;
}

interface ModelSelectorProps {
  selectedModelId: string;
  onModelChange: (modelId: string) => void;
}

const PROVIDER_COLORS: Record<string, string> = {
  anthropic: '#d97706',
  openai: '#10b981',
  xai: '#8b5cf6',
  google: '#3b82f6',
};

export function ModelSelector({ selectedModelId, onModelChange }: ModelSelectorProps) {
  const [models, setModels] = useState<ChatModel[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then(r => r.json())
      .then(data => {
        setModels(data.models || []);
      })
      .catch(err => console.error('Failed to fetch models:', err));
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selected = models.find(m => m.id === selectedModelId);

  if (models.length === 0) return null;

  return (
    <div className="model-selector" ref={ref}>
      <button
        className="model-selector-trigger"
        onClick={() => setOpen(!open)}
        type="button"
      >
        {selected && (
          <span
            className="provider-dot"
            style={{ background: PROVIDER_COLORS[selected.provider] || '#64748b' }}
          />
        )}
        <span className="model-label">{selected?.label || 'Select model'}</span>
        <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" className={`chevron ${open ? 'open' : ''}`}>
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </button>

      {open && (
        <ul className="model-selector-dropdown">
          {models.map(m => (
            <li
              key={m.id}
              className={`model-option ${m.id === selectedModelId ? 'active' : ''}`}
              onClick={() => { onModelChange(m.id); setOpen(false); }}
            >
              <span
                className="provider-dot"
                style={{ background: PROVIDER_COLORS[m.provider] || '#64748b' }}
              />
              <span className="model-option-label">{m.label}</span>
              <span className="model-option-provider">{m.provider}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
