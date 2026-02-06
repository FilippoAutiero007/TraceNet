import { useState } from 'react';
import { NetworkInput } from '@/components/NetworkInput';
import { DownloadResult } from '@/components/DownloadResult';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface SubnetInfo {
  name: string;
  network: string;
  gateway: string;
  usable_hosts: number;
}

interface ConfigSummary {
  base_network: string;
  subnets_count: number;
  routers: number;
  switches: number;
  pcs: number;
  routing_protocol: string;
}

interface GenerateResponse {
  success: boolean;
  message?: string;
  error?: string;
  pkt_download_url?: string;
  xml_download_url?: string;
  config_summary?: ConfigSummary;
  subnets?: SubnetInfo[];
}

export function Generator() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (description: string) => {
    setIsGenerating(true);
    setError(null);
    setResult(null);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

    try {
      const response = await fetch(`${API_URL}/api/generate-pkt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description }),
      });

      if (!response.ok) {
        if (response.status === 0 || response.status >= 500) {
          throw new Error('Cannot connect to server. Make sure backend is running on port 8000.');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || `Server error: ${response.status}`);
      }

      const data: GenerateResponse = await response.json();

      if (data.success && data.pkt_download_url) {
        setResult(data);
      } else {
        throw new Error(data.error || data.message || 'Failed to generate network');
      }
    } catch (err) {
      console.error('Generation error:', err);
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Cannot connect to server. Make sure the backend is running at ' + API_URL);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRetry = () => {
    setError(null);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            Network Generator
          </h1>
          <p className="text-slate-400 text-lg">
            Generate Cisco Packet Tracer networks from natural language descriptions
          </p>
        </div>

        {/* Main Content - Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Input */}
          <div className="space-y-6">
            <NetworkInput onGenerate={handleGenerate} isGenerating={isGenerating} />
            
            {/* Error Display */}
            {error && (
              <Alert variant="destructive" className="bg-red-950 border-red-900">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription className="mt-2">
                  {error}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRetry}
                    className="mt-3 w-full border-red-800 hover:bg-red-900"
                  >
                    Try Again
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Right Column - Result */}
          <div className="space-y-6">
            {result && result.success && result.config_summary && result.subnets ? (
              <DownloadResult data={result as any} />
            ) : (
              <div className="flex items-center justify-center h-full min-h-[400px] bg-slate-900 rounded-lg border border-slate-800">
                <div className="text-center text-slate-500 p-8">
                  <svg
                    className="mx-auto h-24 w-24 mb-4 opacity-50"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p className="text-lg font-medium">Your generated network will appear here</p>
                  <p className="text-sm mt-2">Enter a description or select a template to get started</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
