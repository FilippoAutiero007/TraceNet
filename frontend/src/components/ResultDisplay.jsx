import React, { useState } from 'react';
import { 
  Download, Copy, Check, ChevronDown, ChevronUp, 
  Server, Router, Monitor, Globe, AlertCircle
} from 'lucide-react';

const ResultDisplay = ({ result }) => {
  const [copied, setCopied] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const [showCli, setShowCli] = useState(true);

  if (!result) return null;

  const { success, config_json, subnets, cli_script, error } = result;

  if (!success) {
    return (
      <div className="bg-terminal-surface border border-terminal-error/50 rounded-lg p-6" data-testid="error-display">
        <div className="flex items-center gap-3 text-terminal-error">
          <AlertCircle className="w-5 h-5" />
          <span className="font-semibold">Generation Failed</span>
        </div>
        <p className="mt-2 text-terminal-muted text-sm">{error}</p>
      </div>
    );
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(cli_script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const downloadConfig = () => {
    const blob = new Blob([cli_script], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cisco_config.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4" data-testid="result-display">
      {/* Network Summary */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-terminal-text mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-terminal-accent" />
          Network Summary
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-terminal-bg p-4 rounded-lg border border-terminal-border">
            <div className="flex items-center gap-2 text-terminal-muted text-xs mb-1">
              <Globe className="w-3 h-3" />
              Base Network
            </div>
            <p className="text-terminal-accent font-mono text-sm" data-testid="base-network">
              {config_json?.base_network}
            </p>
          </div>
          
          <div className="bg-terminal-bg p-4 rounded-lg border border-terminal-border">
            <div className="flex items-center gap-2 text-terminal-muted text-xs mb-1">
              <Router className="w-3 h-3" />
              Routers
            </div>
            <p className="text-terminal-green font-mono text-lg" data-testid="router-count">
              {config_json?.devices?.routers || 0}
            </p>
          </div>
          
          <div className="bg-terminal-bg p-4 rounded-lg border border-terminal-border">
            <div className="flex items-center gap-2 text-terminal-muted text-xs mb-1">
              <Server className="w-3 h-3" />
              Switches
            </div>
            <p className="text-terminal-cyan font-mono text-lg" data-testid="switch-count">
              {config_json?.devices?.switches || 0}
            </p>
          </div>
          
          <div className="bg-terminal-bg p-4 rounded-lg border border-terminal-border">
            <div className="flex items-center gap-2 text-terminal-muted text-xs mb-1">
              <Monitor className="w-3 h-3" />
              PCs
            </div>
            <p className="text-terminal-warning font-mono text-lg" data-testid="pc-count">
              {config_json?.devices?.pcs || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Subnet Table */}
      {subnets && subnets.length > 0 && (
        <div className="bg-terminal-surface border border-terminal-border rounded-lg overflow-hidden">
          <div className="p-4 border-b border-terminal-border">
            <h3 className="text-lg font-semibold text-terminal-text">
              Subnet Allocation (VLSM)
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="subnet-table">
              <thead className="bg-terminal-bg">
                <tr className="text-terminal-muted text-xs uppercase">
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Network</th>
                  <th className="px-4 py-3 text-left">Mask</th>
                  <th className="px-4 py-3 text-left">Gateway</th>
                  <th className="px-4 py-3 text-left">Usable Range</th>
                  <th className="px-4 py-3 text-left">Hosts</th>
                </tr>
              </thead>
              <tbody>
                {subnets.map((subnet, index) => (
                  <tr 
                    key={index} 
                    className="border-t border-terminal-border hover:bg-terminal-bg/50 transition-colors"
                    data-testid={`subnet-row-${index}`}
                  >
                    <td className="px-4 py-3 font-medium text-terminal-accent">{subnet.name}</td>
                    <td className="px-4 py-3 font-mono text-terminal-text">{subnet.network}</td>
                    <td className="px-4 py-3 font-mono text-terminal-muted">{subnet.mask}</td>
                    <td className="px-4 py-3 font-mono text-terminal-green">{subnet.gateway}</td>
                    <td className="px-4 py-3 font-mono text-terminal-muted text-xs">
                      {subnet.usable_range[0]} - {subnet.usable_range[1]}
                    </td>
                    <td className="px-4 py-3 font-mono text-terminal-cyan">{subnet.usable_hosts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* JSON Config Collapsible */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg overflow-hidden">
        <button
          onClick={() => setShowJson(!showJson)}
          className="w-full p-4 flex items-center justify-between hover:bg-terminal-bg/30 transition-colors"
          data-testid="toggle-json-button"
        >
          <span className="font-semibold text-terminal-text">Parsed Configuration (JSON)</span>
          {showJson ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        
        {showJson && (
          <div className="p-4 border-t border-terminal-border bg-terminal-bg">
            <pre className="text-xs text-terminal-text overflow-x-auto" data-testid="json-preview">
              {JSON.stringify(config_json, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* CLI Script */}
      <div className="bg-terminal-surface border border-terminal-border rounded-lg overflow-hidden">
        <div className="p-4 border-b border-terminal-border flex items-center justify-between">
          <button
            onClick={() => setShowCli(!showCli)}
            className="flex items-center gap-2 font-semibold text-terminal-text"
            data-testid="toggle-cli-button"
          >
            Cisco IOS Configuration
            {showCli ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
          
          <div className="flex gap-2">
            <button
              onClick={copyToClipboard}
              data-testid="copy-config-button"
              className="flex items-center gap-2 px-3 py-1.5 bg-terminal-bg border border-terminal-border 
                         rounded text-sm text-terminal-muted hover:text-terminal-text 
                         hover:border-terminal-accent transition-all"
            >
              {copied ? <Check className="w-4 h-4 text-terminal-success" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            
            <button
              onClick={downloadConfig}
              data-testid="download-config-button"
              className="flex items-center gap-2 px-3 py-1.5 bg-terminal-accent text-terminal-bg
                         rounded text-sm font-medium hover:bg-terminal-accent/90 transition-all"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>
        
        {showCli && (
          <div className="p-4 bg-terminal-bg max-h-96 overflow-y-auto">
            <pre className="text-xs text-terminal-green font-mono whitespace-pre-wrap" data-testid="cli-script">
              {cli_script}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultDisplay;
