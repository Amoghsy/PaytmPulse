/**
 * Paytm Pulse - Frontend Voice Engine (STT & TTS)
 * Seamlessly combines high-performance in-browser Web Speech API (zero latency)
 * with Sarvam AI Indian-language speech synthesis and recognition.
 */

const LANGUAGE_CODE_MAP = {
  'en': 'en-IN',
  'kn': 'kn-IN',
  'hi': 'hi-IN',
  'mr': 'mr-IN',
  'ta': 'ta-IN',
  'te': 'te-IN',
  'en-IN': 'en-IN',
  'kannada': 'kn-IN',
  'hindi': 'hi-IN',
  'english': 'en-IN'
};

/**
 * Checks if browser supports Speech Recognition (Listening)
 */
export function isSpeechRecognitionSupported() {
  return typeof window !== 'undefined' && Boolean(
    window.SpeechRecognition || window.webkitSpeechRecognition
  );
}

/**
 * Checks if browser supports Speech Synthesis (Speaking)
 */
export function isSpeechSynthesisSupported() {
  return typeof window !== 'undefined' && Boolean(window.speechSynthesis);
}

/**
 * Clean markdown formatting, bullet symbols, and special characters before speaking
 */
export function cleanTextForSpeech(rawText) {
  if (!rawText) return '';
  return rawText
    .replace(/\*\*(.*?)\*\*/g, '$1')  // remove bold asterisks
    .replace(/\*(.*?)\*/g, '$1')      // remove italic asterisks
    .replace(/•/g, '')               // remove bullet dots
    .replace(/#{1,6}\s+/g, '')        // remove headers
    .replace(/\[(.*?)\]\(.*?\)/g, '$1') // remove links
    .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // remove emojis
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Start listening to user voice and transcribing in real-time
 */
export function startListening({
  language = 'en',
  onResult,
  onError,
  onEnd
}) {
  if (!isSpeechRecognitionSupported()) {
    if (onError) onError(new Error('Speech recognition is not supported in this browser. Please use Chrome or Edge.'));
    return null;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  const langCode = LANGUAGE_CODE_MAP[language.toLowerCase()] || 'en-IN';
  recognition.lang = langCode;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  let finalTranscript = '';

  recognition.onresult = (event) => {
    let interimTranscript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }
    if (onResult) {
      onResult({
        transcript: finalTranscript || interimTranscript,
        isFinal: Boolean(finalTranscript),
        raw: interimTranscript
      });
    }
  };

  recognition.onerror = (event) => {
    console.warn('Speech recognition error:', event.error);
    if (onError) onError(event);
  };

  recognition.onend = () => {
    if (onEnd) onEnd({ transcript: finalTranscript });
  };

  try {
    recognition.start();
    return recognition;
  } catch (err) {
    if (onError) onError(err);
    return null;
  }
}

/**
 * Stop any ongoing speech synthesis
 */
export function stopSpeaking() {
  if (isSpeechSynthesisSupported()) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Speaks text out loud in the matching regional language voice
 */
export function speakText({
  text,
  language = 'en',
  onStart,
  onEnd,
  onError
}) {
  if (!isSpeechSynthesisSupported() || !text) {
    if (onEnd) onEnd();
    return;
  }

  // Stop any active utterance first
  stopSpeaking();

  const clean = cleanTextForSpeech(text);
  if (!clean) {
    if (onEnd) onEnd();
    return;
  }

  const utterance = new SpeechSynthesisUtterance(clean);
  const langCode = LANGUAGE_CODE_MAP[language.toLowerCase()] || 'en-IN';
  utterance.lang = langCode;
  utterance.rate = 0.98; // Natural, conversational pace
  utterance.pitch = 1.0;

  // Select appropriate voice if available in system
  const voices = window.speechSynthesis.getVoices();
  if (voices && voices.length > 0) {
    const matchingVoice = voices.find(v => v.lang === langCode || v.lang.startsWith(langCode.slice(0, 2))) ||
      voices.find(v => v.lang.includes('en-IN') || v.name.includes('India') || v.name.includes('Indian')) ||
      voices[0];
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }
  }

  utterance.onstart = () => {
    if (onStart) onStart();
  };

  utterance.onend = () => {
    if (onEnd) onEnd();
  };

  utterance.onerror = (e) => {
    console.warn('Speech synthesis error:', e);
    if (onError) onError(e);
    if (onEnd) onEnd();
  };

  window.speechSynthesis.speak(utterance);
}
