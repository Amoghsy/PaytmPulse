import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, 
  Send, 
  Trash2, 
  Mic, 
  MicOff,
  Bot, 
  User, 
  Store, 
  Zap, 
  TrendingUp, 
  AlertCircle,
  Globe,
  Volume2,
  VolumeX,
  Radio
} from 'lucide-react';
import PageHeader from '../layout/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import ChatBubble from '../components/ChatBubble';
import { sendAgentChatMessage, clearMerchantConversationMemory } from '../services/api';
import { 
  startListening, 
  speakText, 
  stopSpeaking, 
  isSpeechRecognitionSupported, 
  isSpeechSynthesisSupported 
} from '../services/voice';

const LANGUAGE_OPTIONS = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'hi', label: 'हिंदी (Hindi)' },
  { code: 'mr', label: 'मराठी (Marathi)' },
  { code: 'en-IN', label: 'Hinglish / Kanglish' },
];

export default function Advisor({ 
  currentMerchant, 
  conversationMemory = [], 
  onRefreshData,
  onShowToast 
}) {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState(
    currentMerchant?.preferred_language || 'en'
  );

  // Voice Module States
  const [isListening, setIsListening] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const recognitionRef = useRef(null);

  // Sync selected language if merchant changes
  useEffect(() => {
    if (currentMerchant?.preferred_language) {
      setSelectedLanguage(currentMerchant.preferred_language);
    }
  }, [currentMerchant?.id, currentMerchant?.preferred_language]);

  // Clean up any ongoing speech synthesis or listening on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, []);

  // Suggested prompt chips
  const suggestedPrompts = [
    { text: "Which item will run out today?", icon: Zap },
    { text: "Show at-risk customers", icon: AlertCircle },
    { text: "How can I increase evening sales?", icon: TrendingUp },
    { text: "What are my top selling products this week?", icon: Store },
  ];

  const loadedMerchantRef = useRef(null);

  // Initialize and sync messages only when active merchant changes (prevents polling wipeouts)
  useEffect(() => {
    if (!currentMerchant?.id) return;

    if (loadedMerchantRef.current === currentMerchant.id) {
      return;
    }
    loadedMerchantRef.current = currentMerchant.id;

    if (conversationMemory && conversationMemory.length > 0) {
      const formatted = conversationMemory.map((item, idx) => ({
        id: item.id || `msg-${idx}`,
        role: item.role === 'user' ? 'user' : 'assistant',
        text: item.content || item.message || (typeof item === 'string' ? item : JSON.stringify(item)),
        timestamp: item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'
      }));
      setMessages(formatted);
    } else {
      // Default welcome message if empty
      setMessages([
        {
          id: `welcome-${currentMerchant.id}`,
          role: 'assistant',
          text: `Namaste! I am your Paytm Pulse AI Business Partner for **${currentMerchant?.shop_name || currentMerchant?.business_name || 'your store'}**.\n\nAsk me anything by typing or using your microphone in Kannada, Hindi, or English!`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  }, [currentMerchant?.id]);

  const chatScrollRef = useRef(null);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTo({
        top: chatScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isSending]);

  // Voice speaking handler for a specific message
  const handleSpeakMessage = (id, text) => {
    setSpeakingMessageId(id);
    speakText({
      text,
      language: selectedLanguage,
      onStart: () => setSpeakingMessageId(id),
      onEnd: () => setSpeakingMessageId(null),
      onError: () => setSpeakingMessageId(null)
    });
  };

  const handleStopSpeak = () => {
    stopSpeaking();
    setSpeakingMessageId(null);
  };

  // Voice listening handler (STT)
  const handleToggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setIsListening(false);
      return;
    }

    if (!isSpeechRecognitionSupported()) {
      if (onShowToast) {
        onShowToast({
          type: 'warning',
          message: 'Speech recognition is not supported in this browser. Please use Chrome or Edge.'
        });
      }
      return;
    }

    // Stop speaking if currently speaking
    stopSpeaking();
    setSpeakingMessageId(null);

    setIsListening(true);
    const recognition = startListening({
      language: selectedLanguage,
      onResult: ({ transcript, isFinal }) => {
        setInputText(transcript);
      },
      onError: (err) => {
        console.warn('Speech recognition error:', err);
        setIsListening(false);
      },
      onEnd: () => {
        setIsListening(false);
      }
    });

    recognitionRef.current = recognition;
  };

  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputText).trim();
    if (!text || !currentMerchant?.id || isSending) return;

    // Stop any active listening or speaking
    if (isListening && recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      setIsListening(false);
    }
    stopSpeaking();
    setSpeakingMessageId(null);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsSending(true);

    try {
      const response = await sendAgentChatMessage(currentMerchant.id, text, selectedLanguage);
      if (response.ok && response.data) {
        const reply = response.data.reply || response.data.response || response.data.message || 'No response generated.';
        const botMsgId = `bot-${Date.now()}`;
        const assistantMessage = {
          id: botMsgId,
          role: 'assistant',
          text: reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, assistantMessage]);
        if (onRefreshData) onRefreshData();

        // Auto-speak if enabled
        if (autoSpeak) {
          handleSpeakMessage(botMsgId, reply);
        }
      } else {
        const errorMsg = response.data?.error || response.data?.detail || 'Failed to get a response from AI advisor.';
        setMessages(prev => [
          ...prev, 
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            text: `**Error:** ${errorMsg}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
        if (onShowToast) onShowToast({ type: 'error', message: errorMsg });
      }
    } catch (err) {
      setMessages(prev => [
        ...prev, 
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          text: `**Network Error:** Failed to connect to Paytm Pulse backend.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      if (onShowToast) onShowToast({ type: 'error', message: 'Failed to connect to AI Advisor.' });
    } finally {
      setIsSending(false);
    }
  };

  const handleClearChat = async () => {
    if (!currentMerchant?.id || isClearing) return;
    setIsClearing(true);
    stopSpeaking();
    setSpeakingMessageId(null);
    try {
      await clearMerchantConversationMemory(currentMerchant.id);
      setMessages([
        {
          id: `welcome-${Date.now()}`,
          role: 'assistant',
          text: `Conversation history cleared. How can I help ${currentMerchant?.business_name || 'your store'} today?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      if (onShowToast) onShowToast({ type: 'info', message: 'Chat conversation reset.' });
      if (onRefreshData) onRefreshData();
    } catch (err) {
      if (onShowToast) onShowToast({ type: 'error', message: 'Failed to reset conversation memory.' });
    } finally {
      setIsClearing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getLanguageLabel = () => {
    const found = LANGUAGE_OPTIONS.find(l => l.code === selectedLanguage);
    return found ? found.label.split(' ')[0] : 'English';
  };

  return (
    <div className="page-container" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <PageHeader
        title="AI Business Partner Advisor"
        description={`Interactive reasoning agent powered by Google Gemini and real-time merchant memory for ${currentMerchant?.business_name || 'Store'}.`}
        tag="Voice & Agent Reasoning"
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button
              variant="secondary"
              size="sm"
              icon={<Trash2 size={15} />}
              onClick={handleClearChat}
              disabled={isClearing || isSending}
            >
              Clear Chat
            </Button>
          </div>
        }
      />

      <Card 
        noPadding={true}
        style={{ 
          height: 'calc(100vh - 200px)', 
          minHeight: '580px',
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid var(--border-color)',
          boxShadow: 'var(--shadow-sm)'
        }}
      >
        {/* Chat Card Header */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'var(--surface-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--paytm-navy), var(--paytm-cyan))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              boxShadow: '0 2px 6px rgba(0, 185, 245, 0.25)'
            }}>
              <Sparkles size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)' }}>Pulse AI</span>
                <span style={{ 
                  fontSize: '11px', 
                  fontWeight: 600, 
                  background: 'var(--info-tint)', 
                  color: 'var(--paytm-navy)', 
                  padding: '2px 8px', 
                  borderRadius: '10px' 
                }}>
                  Voice Enabled &bull; Gemini ADK
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success-color)' }}></span>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Online &bull; Context: {currentMerchant?.business_name} ({currentMerchant?.category})
                </span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Auto-Speak Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextState = !autoSpeak;
                setAutoSpeak(nextState);
                if (!nextState) stopSpeaking();
              }}
              title={autoSpeak ? "Auto-Speak enabled: Responses will be read out aloud" : "Click to enable Auto-Speak"}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 10px',
                borderRadius: '8px',
                border: autoSpeak ? '1px solid var(--paytm-cyan)' : '1px solid var(--border-color)',
                background: autoSpeak ? 'var(--info-tint)' : 'var(--page-bg)',
                color: autoSpeak ? 'var(--paytm-navy)' : 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {autoSpeak ? (
                <>
                  <Volume2 size={14} color="var(--paytm-cyan)" />
                  <span>Auto-Speak: ON</span>
                </>
              ) : (
                <>
                  <VolumeX size={14} />
                  <span>Auto-Speak: OFF</span>
                </>
              )}
            </button>

            {/* Interactive Language Switcher */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              background: 'var(--page-bg)', 
              padding: '4px 10px', 
              borderRadius: '8px',
              border: '1px solid var(--border-color)'
            }}>
              <Globe size={14} style={{ color: 'var(--paytm-navy)' }} />
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>Language:</span>
              <select
                value={selectedLanguage}
                onChange={(e) => {
                  setSelectedLanguage(e.target.value);
                  stopSpeaking();
                  setSpeakingMessageId(null);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--paytm-navy)',
                  cursor: 'pointer',
                  outline: 'none',
                  padding: '2px 4px'
                }}
              >
                {LANGUAGE_OPTIONS.map((opt) => (
                  <option key={opt.code} value={opt.code}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Message Stream Area */}
        <div 
          ref={chatScrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            background: 'var(--page-bg)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            minHeight: 0
          }}
        >
          {messages.map((msg) => (
            <ChatBubble
              key={msg.id}
              role={msg.role}
              text={msg.text}
              timestamp={msg.timestamp}
              isSpeaking={speakingMessageId === msg.id}
              onSpeak={(text) => handleSpeakMessage(msg.id, text)}
              onStopSpeak={handleStopSpeak}
            />
          ))}

          {isSending && (
            <ChatBubble
              role="assistant"
              isTyping={true}
            />
          )}
        </div>

        {/* Listening Active Banner */}
        {isListening && (
          <div style={{
            padding: '8px 16px',
            background: 'linear-gradient(90deg, #E6F8FE 0%, #F0FDF4 100%)',
            borderTop: '1px solid #BAE6FD',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: '#EF4444',
                boxShadow: '0 0 8px #EF4444',
                animation: 'pulse 1s infinite'
              }} />
              <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--paytm-navy)' }}>
                🎙️ Listening in {getLanguageLabel()}... Speak now
              </span>
            </div>
            <button
              type="button"
              onClick={handleToggleListening}
              style={{
                border: 'none',
                background: '#EF4444',
                color: '#fff',
                fontSize: '11px',
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Done / Stop
            </button>
          </div>
        )}

        {/* Suggested Prompt Chips */}
        <div style={{
          padding: '10px 16px',
          background: 'var(--surface-color)',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          scrollbarWidth: 'none',
          flexShrink: 0
        }}>
          {suggestedPrompts.map((prompt, idx) => {
            const Icon = prompt.icon;
            return (
              <button
                key={idx}
                onClick={() => handleSendMessage(prompt.text)}
                disabled={isSending}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '16px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--surface-color)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: isSending ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--paytm-cyan)';
                  e.currentTarget.style.background = 'var(--info-tint)';
                  e.currentTarget.style.color = 'var(--paytm-navy)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                  e.currentTarget.style.background = 'var(--surface-color)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
              >
                <Icon size={13} color="var(--paytm-cyan)" />
                {prompt.text}
              </button>
            );
          })}
        </div>

        {/* Input Bar */}
        <div style={{
          padding: '14px 16px',
          background: 'var(--surface-color)',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'flex-end',
          gap: '10px',
          flexShrink: 0
        }}>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening to your voice..." : `Ask Pulse AI about ${currentMerchant?.business_name || 'your store'}... (Type or click Mic)`}
            rows={1}
            disabled={isSending}
            style={{
              flex: 1,
              resize: 'none',
              padding: '10px 14px',
              borderRadius: '10px',
              border: isListening ? '1.5px solid #EF4444' : '1px solid var(--border-color)',
              background: isListening ? '#FEF2F2' : 'var(--surface-color)',
              color: 'var(--text-primary)',
              fontSize: '14px',
              fontFamily: 'inherit',
              lineHeight: '1.4',
              maxHeight: '100px',
              outline: 'none',
              transition: 'all 0.15s ease'
            }}
            onFocus={(e) => { if (!isListening) e.target.style.borderColor = 'var(--paytm-cyan)'; }}
            onBlur={(e) => { if (!isListening) e.target.style.borderColor = 'var(--border-color)'; }}
          />

          {/* Voice Microphone Input Button */}
          <button
            type="button"
            onClick={handleToggleListening}
            title={isListening ? "Stop listening" : `Speak in ${getLanguageLabel()}`}
            disabled={isSending}
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              border: isListening ? '1.5px solid #EF4444' : '1px solid var(--border-color)',
              background: isListening ? '#EF4444' : 'var(--page-bg)',
              color: isListening ? '#FFFFFF' : 'var(--paytm-navy)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: isSending ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: isListening ? '0 0 12px rgba(239, 68, 68, 0.4)' : 'none'
            }}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          <Button
            variant="primary"
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim() || isSending}
            loading={isSending}
            icon={<Send size={16} />}
          >
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
}

