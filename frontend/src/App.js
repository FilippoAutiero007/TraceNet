import React, { useState, useEffect } from 'react';
import { Terminal, Wifi, WifiOff, Github } from 'lucide-react';
import InputForm from './components/InputForm';
import ResultDisplay from './components/ResultDisplay';
import LoadingSpinner from './components/LoadingSpinner';
import { generateNetwork, healthCheck } from './services/api';

function App() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkApi = async () => {
      try {
        await healthCheck();
        setApiStatus('online');
      } catch (err) {
        setApiStatus('offline');
      }
    };
    checkApi();
    const interval = setInterval(checkApi, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerate = async (description) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await generateNetwork(description);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate configuration');
      setResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Failed to generate configuration'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-terminal-bg">
      {/* Header */}
      <header className="border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-terminal-accent/10 rounded-lg">
              <Terminal className="w-6 h-6 text-terminal-accent" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-terminal-text tracking-tight">
                NetTrace
              </h1>
              <p className="text-xs text-terminal-muted">
                Natural Language → Cisco Config
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div 
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
                ${apiStatus === 'online' 
                  ? 'bg-terminal-success/10 text-terminal-success' 
                  : apiStatus === 'offline'
                  ? 'bg-terminal-error/10 text-terminal-error'
                  : 'bg-terminal-warning/10 text-terminal-warning'
                }`}
              data-testid="api-status"
            >
              {apiStatus === 'online' ? (
                <>
                  <Wifi className="w-3 h-3" />
                  API Online
                </>
              ) : apiStatus === 'offline' ? (
                <>
                  <WifiOff className="w-3 h-3" />
                  API Offline
                </>
              ) : (
                <>
                  <div className="w-3 h-3 border-2 border-terminal-warning border-t-transparent rounded-full animate-spin" />
                  Checking...
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div>
            <InputForm onSubmit={handleGenerate} isLoading={isLoading} />
            
            {/* Features */}
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="bg-terminal-surface/50 border border-terminal-border rounded-lg p-4">
                <h4 className="text-sm font-medium text-terminal-accent mb-1">VLSM Calculator</h4>
                <p className="text-xs text-terminal-muted">
                  Optimizes IP allocation with Variable Length Subnet Masking
                </p>
              </div>
              <div className="bg-terminal-surface/50 border border-terminal-border rounded-lg p-4">
                <h4 className="text-sm font-medium text-terminal-cyan mb-1">Cisco IOS Output</h4>
                <p className="text-xs text-terminal-muted">
                  Ready-to-use configuration for routers and switches
                </p>
              </div>
            </div>
          </div>

          {/* Output Section */}
          <div>
            {isLoading ? (
              <div className="bg-terminal-surface border border-terminal-border rounded-lg">
                <LoadingSpinner message="Generating network configuration..." />
              </div>
            ) : result ? (
              <ResultDisplay result={result} />
            ) : (
              <div className="bg-terminal-surface border border-terminal-border rounded-lg p-8 
                              flex flex-col items-center justify-center min-h-[400px] text-center">
                <div className="w-16 h-16 bg-terminal-bg rounded-full flex items-center justify-center mb-4">
                  <Terminal className="w-8 h-8 text-terminal-muted" />
                </div>
                <h3 className="text-lg font-medium text-terminal-text mb-2">
                  Ready to Generate
                </h3>
                <p className="text-sm text-terminal-muted max-w-xs">
                  Describe your network topology in natural language and get instant Cisco configurations
                </p>
                <div className="mt-4 flex items-center gap-2 text-xs text-terminal-muted">
                  <span className="text-terminal-cyan">$</span>
                  <span className="cursor-blink">Enter your network description</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* How it Works */}
        <section className="mt-16 border-t border-terminal-border pt-12">
          <h2 className="text-2xl font-bold text-terminal-text text-center mb-8">
            How It Works
          </h2>
          
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6 text-center">
              <div className="w-12 h-12 bg-terminal-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-terminal-accent">1</span>
              </div>
              <h3 className="font-semibold text-terminal-text mb-2">Describe</h3>
              <p className="text-sm text-terminal-muted">
                Write your network requirements in plain English
              </p>
            </div>
            
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6 text-center">
              <div className="w-12 h-12 bg-terminal-cyan/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-terminal-cyan">2</span>
              </div>
              <h3 className="font-semibold text-terminal-text mb-2">Process</h3>
              <p className="text-sm text-terminal-muted">
                AI parses your description and calculates optimal subnets
              </p>
            </div>
            
            <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6 text-center">
              <div className="w-12 h-12 bg-terminal-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-terminal-success">3</span>
              </div>
              <h3 className="font-semibold text-terminal-text mb-2">Download</h3>
              <p className="text-sm text-terminal-muted">
                Get ready-to-use Cisco IOS configuration files
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-terminal-border mt-16 py-6">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between text-xs text-terminal-muted">
          <span>© 2024 NetTrace - Network Configuration Generator</span>
          <span className="flex items-center gap-1">
            Built with <span className="text-terminal-error">♥</span> for network engineers
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
