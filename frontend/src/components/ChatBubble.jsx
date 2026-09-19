import React from 'react';
import { Bot, User, Volume2, Square, VolumeX } from 'lucide-react';

function renderFormattedText(text) {
  if (!text) return '';
  const lines = text.split('\n');
  return lines.map((line, lIdx) => {
    // Check bullet points
    const isBullet = line.trim().startsWith('•') || line.trim().startsWith('* ') || line.trim().startsWith('- ');
    let cleanLine = isBullet ? line.trim().replace(/^[\*\•\-]\s*/, '') : line;

    // Parse **bold** tokens
    const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
    const renderedParts = parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={pIdx} style={{ color: 'var(--color-paytm-navy)', fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    if (isBullet) {
      return (
        <div key={lIdx} style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', margin: '3px 0' }}>
          <span style={{ color: 'var(--color-paytm-cyan)', fontWeight: 700 }}>•</span>
          <span style={{ flex: 1 }}>{renderedParts}</span>
        </div>
      );
    }

    if (line.trim() === '') {
      return <div key={lIdx} style={{ height: '6px' }} />;
    }

    return <div key={lIdx} style={{ margin: '2px 0' }}>{renderedParts}</div>;
  });
}

export function ChatBubble({
  message,
  role,
  text,
  timestamp,
  isTyping = false,
  isSpeaking = false,
  onSpeak,
  onStopSpeak
}) {
  const isUser = (role === 'user') || (message && (message.sender === 'user' || message.role === 'user'));
  const msgText = text || (message && (message.text || message.content)) || '';
  const time = timestamp || (message && (message.time || message.timestamp)) || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (isTyping) {
    return (
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '14px' }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-paytm-cyan-tint)',
            color: 'var(--color-text-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <Bot size={16} />
        </div>
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#FFFFFF',
            border: '1px solid var(--color-border)',
            borderRadius: '16px 16px 16px 4px',
            boxShadow: 'var(--shadow-xs)',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-text-muted)', animation: 'live-pulse 1s infinite' }} />
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-text-muted)', animation: 'live-pulse 1s infinite 0.2s' }} />
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-text-muted)', animation: 'live-pulse 1s infinite 0.4s' }} />
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        gap: '8px',
        marginBottom: '14px'
      }}
    >
      {!isUser && (
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: isSpeaking ? 'var(--color-paytm-cyan)' : 'var(--color-paytm-cyan-tint)',
            color: isSpeaking ? '#FFFFFF' : 'var(--color-text-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'all 0.2s ease',
            boxShadow: isSpeaking ? '0 0 10px rgba(0, 185, 245, 0.4)' : 'none'
          }}
        >
          <Bot size={16} />
        </div>
      )}

      <div
        style={{
          maxWidth: '82%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start'
        }}
      >
        <div
          style={{
            padding: '12px 16px',
            borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
            backgroundColor: isUser ? 'var(--color-paytm-cyan-tint)' : '#FFFFFF',
            border: isUser
              ? '1px solid var(--color-paytm-cyan)'
              : isSpeaking
              ? '1px solid var(--color-paytm-cyan)'
              : '1px solid var(--color-border)',
            color: 'var(--color-text-primary)',
            fontSize: '13.5px',
            lineHeight: 1.55,
            boxShadow: isSpeaking ? '0 2px 12px rgba(0, 185, 245, 0.15)' : 'var(--shadow-xs)',
            transition: 'all 0.2s ease'
          }}
        >
          {renderFormattedText(msgText)}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', padding: '0 4px' }}>
          <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
            {time}
          </span>

          {!isUser && msgText && onSpeak && (
            <button
              type="button"
              onClick={() => {
                if (isSpeaking && onStopSpeak) {
                  onStopSpeak();
                } else {
                  onSpeak(msgText);
                }
              }}
              title={isSpeaking ? "Stop Speaking" : "Listen in Voice"}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: isSpeaking ? '#E6F8FE' : 'transparent',
                border: 'none',
                color: isSpeaking ? '#0079A6' : 'var(--color-text-muted)',
                fontSize: '11px',
                fontWeight: isSpeaking ? 600 : 400,
                cursor: 'pointer',
                padding: '2px 6px',
                borderRadius: '6px',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                if (!isSpeaking) {
                  e.currentTarget.style.color = 'var(--color-paytm-navy)';
                  e.currentTarget.style.backgroundColor = '#F1F5F9';
                }
              }}
              onMouseLeave={(e) => {
                if (!isSpeaking) {
                  e.currentTarget.style.color = 'var(--color-text-muted)';
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {isSpeaking ? (
                <>
                  <Square size={11} fill="#0079A6" color="#0079A6" />
                  <span>Speaking...</span>
                </>
              ) : (
                <>
                  <Volume2 size={12} />
                  <span>Listen</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {isUser && (
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-paytm-navy)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <User size={16} />
        </div>
      )}
    </div>
  );
}

export default ChatBubble;
