const LoadingSpinner = () => {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
        </div>
        <span className="text-slate-400 text-sm ml-1">Solving...</span>
      </div>
    </div>
  );
};

export default LoadingSpinner;
