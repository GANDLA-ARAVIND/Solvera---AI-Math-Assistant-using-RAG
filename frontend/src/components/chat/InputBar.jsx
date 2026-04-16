import { useState, useRef, useEffect } from 'react';
import useChatStore from '../../store/chatStore';
import useSpeechRecognition from '../../hooks/useSpeechRecognition';
import { Send, ImagePlus, Mic, MicOff, FileText } from 'lucide-react';

const InputBar = () => {
  const [query, setQuery] = useState('');
  const fileInputRef = useRef(null);
  const pdfInputRef = useRef(null);
  const { sendQuery, sendImage, sendPdf, isLoading, pdfContext } = useChatStore();
  const { isListening, transcript, startListening, stopListening, resetTranscript, isSupported } = useSpeechRecognition();

  useEffect(() => {
    if (transcript) {
      setQuery(transcript);
    }
  }, [transcript]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    sendQuery(query.trim());
    setQuery('');
    resetTranscript();
  };

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      sendImage(file);
      fileInputRef.current.value = '';
    }
  };

  const handlePdfUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      sendPdf(file);
      pdfInputRef.current.value = '';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{ flexShrink: 0 }}
      className="border-t border-slate-700 bg-slate-900/50 p-4 flex items-center gap-2"
    >
      <button
        type="button"
        onClick={() => fileInputRef.current.click()}
        className="p-2.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-700 transition-colors"
        title="Upload image of math problem"
        disabled={isLoading}
      >
        <ImagePlus size={20} />
      </button>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleImageUpload}
        accept="image/*"
        className="hidden"
      />
      <button
        type="button"
        onClick={() => pdfInputRef.current.click()}
        className="p-2.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-700 transition-colors"
        title="Upload math PDF"
        disabled={isLoading}
      >
        <FileText size={20} />
      </button>
      <input
        type="file"
        ref={pdfInputRef}
        onChange={handlePdfUpload}
        accept=".pdf"
        className="hidden"
      />
      {isSupported && (
        <button
          type="button"
          onClick={handleMicClick}
          className={`p-2.5 rounded-xl transition-all ${isListening
            ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 animate-pulse'
            : 'text-slate-400 hover:text-white hover:bg-slate-700'
            }`}
          title={isListening ? "Stop recording" : "Use voice input"}
          disabled={isLoading}
        >
          {isListening ? <MicOff size={20} /> : <Mic size={20} />}
        </button>
      )}
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={pdfContext ? "Ask a question about the uploaded PDF..." : "Ask a math question... (e.g., Solve x² + 3x - 4 = 0)"}
        className="flex-1 bg-slate-800 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 border border-slate-600 placeholder-slate-500"
        disabled={isLoading}
      />
      <button
        type="submit"
        disabled={isLoading || !query.trim()}
        className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <Send size={18} />
      </button>
    </form>
  );
};

export default InputBar;
