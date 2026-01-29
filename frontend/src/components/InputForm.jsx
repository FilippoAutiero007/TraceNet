import React, { useState } from 'react';
import { Network, Send, Loader2 } from 'lucide-react';

const InputForm = ({ onSubmit, isLoading }) => {
  const [description, setDescription] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (description.trim() && !isLoading) {
      onSubmit(description);
    }
  };

  const examplePrompts = [
    "Create 3 subnets with 50 hosts each from 192.168.1.0/24 with 1 router and 3 switches",
    "I need 4 networks: 100 hosts, 50 hosts, 25 hosts, and 10 hosts using 10.0.0.0/16 with OSPF routing",
    "Setup 2 subnets for 30 users each from 172.16.0.0/24 with RIP protocol"
  ];

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-terminal-accent/10 rounded-lg">
          <Network className="w-5 h-5 text-terminal-accent" />
        </div>
        <h2 className="text-lg font-semibold text-terminal-text">
          Network Description
        </h2>
      </div>

      <form onSubmit={handleSubmit}>
        <textarea
          data-testid="network-description-input"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe your network topology in natural language...&#10;&#10;Example: Create 3 subnets with 50 hosts each from 192.168.1.0/24"
          className="w-full h-40 bg-terminal-bg border border-terminal-border rounded-lg p-4 
                     text-terminal-text placeholder-terminal-muted resize-none
                     focus:outline-none focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent
                     transition-all duration-200 font-mono text-sm"
          disabled={isLoading}
        />

        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-terminal-muted">
            {description.length} characters
          </span>
          
          <button
            type="submit"
            data-testid="generate-button"
            disabled={!description.trim() || isLoading}
            className="flex items-center gap-2 px-6 py-2.5 bg-terminal-accent text-terminal-bg
                       rounded-lg font-medium transition-all duration-200
                       hover:bg-terminal-accent/90 hover:shadow-lg hover:shadow-terminal-accent/20
                       disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Generate Config
              </>
            )}
          </button>
        </div>
      </form>

      <div className="mt-6 pt-4 border-t border-terminal-border">
        <p className="text-xs text-terminal-muted mb-3">Quick examples:</p>
        <div className="space-y-2">
          {examplePrompts.map((prompt, index) => (
            <button
              key={index}
              data-testid={`example-prompt-${index}`}
              onClick={() => setDescription(prompt)}
              className="w-full text-left px-3 py-2 bg-terminal-bg border border-terminal-border 
                         rounded text-xs text-terminal-muted hover:text-terminal-text 
                         hover:border-terminal-accent/50 transition-all duration-200"
              disabled={isLoading}
            >
              <span className="text-terminal-cyan">$</span> {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default InputForm;
