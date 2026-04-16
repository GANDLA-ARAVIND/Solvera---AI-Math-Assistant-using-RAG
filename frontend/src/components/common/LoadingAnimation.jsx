import { Brain } from 'lucide-react';

const LoadingAnimation = () => {
  return (
    <div className="flex justify-start mb-4 solvera-msg-appear">
      <div className="loading-bubble max-w-[80%] rounded-2xl rounded-bl-sm px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="loading-brain-icon">
            <Brain size={20} />
          </div>
          <div>
            <p className="text-sm font-medium loading-title">Solvera is thinking…</p>
            <div className="flex gap-1.5 mt-2">
              <span className="loading-dot" style={{ animationDelay: '0s' }} />
              <span className="loading-dot" style={{ animationDelay: '0.2s' }} />
              <span className="loading-dot" style={{ animationDelay: '0.4s' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingAnimation;
