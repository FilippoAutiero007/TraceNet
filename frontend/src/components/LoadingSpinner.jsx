import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({ message = 'Processing...' }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12" data-testid="loading-spinner">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-terminal-border rounded-full"></div>
        <div className="absolute top-0 left-0 w-16 h-16 border-4 border-terminal-accent rounded-full 
                        border-t-transparent animate-spin"></div>
      </div>
      <p className="mt-4 text-terminal-muted font-mono text-sm animate-pulse">
        {message}
      </p>
      <div className="mt-2 flex gap-1">
        <span className="w-2 h-2 bg-terminal-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
        <span className="w-2 h-2 bg-terminal-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
        <span className="w-2 h-2 bg-terminal-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
      </div>
    </div>
  );
};

export default LoadingSpinner;
