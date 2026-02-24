import React from 'react';

type Mode = 'chat' | 'voice';

interface ModeToggleProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  disabled?: boolean;
}

export const ModeToggle: React.FC<ModeToggleProps> = ({
  mode,
  onModeChange,
  disabled = false
}) => {
  return (
    <div className="mode-toggle">
      <button
        className={`mode-btn ${mode === 'chat' ? 'active' : ''}`}
        onClick={() => onModeChange('chat')}
        disabled={disabled}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
        </svg>
        <span>Chat</span>
      </button>
      <button
        className={`mode-btn ${mode === 'voice' ? 'active' : ''}`}
        onClick={() => onModeChange('voice')}
        disabled={disabled}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        <span>Voice</span>
      </button>
    </div>
  );
};
