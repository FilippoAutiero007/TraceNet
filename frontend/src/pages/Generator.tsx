import { useState } from 'react';
import { getApiBaseUrl } from '@/lib/api';
import { NetworkInput } from '@/components/NetworkInput';
import { PktAnalyzer } from '@/components/PktAnalyzer';
import { DownloadResult } from '@/components/DownloadResult';
import { SEOHead } from '@/components/SEOHead';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, FileWarning } from 'lucide-react';
import type { PktAnalysisResponse } from '@/lib/api';

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

interface ParseResponse {
  intent: 'not_network' | 'incomplete' | 'complete';
  missing: string[];
  json: Record<string, unknown>;
}

interface DownloadResultData {
  success: true;
  message: string;
  pkt_download_url: string;
  xml_download_url?: string;
  config_summary: ConfigSummary;
  subnets: SubnetInfo[];
}

function isDownloadResultData(result: GenerateResponse | null): result is DownloadResultData {
  return Boolean(
    result &&
    result.success &&
    result.message &&
    result.pkt_download_url &&
    result.config_summary &&
    result.subnets
  );
}

export function Generator() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<Record<string, unknown>>({});
  const [analysisResult, setAnalysisResult] = useState<PktAnalysisResponse | null>(null);

  const handleGenerate = async (description: string) => {
    setIsGenerating(true);
    setError(null);
    setResult(null);

    const apiBaseUrl = getApiBaseUrl();

    try {
      const parseResponse = await fetch(`${apiBaseUrl}/api/parse-network-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: description,
          current_state: conversationState,
        }),
      });

      if (!parseResponse.ok) {
        const errorData = await parseResponse.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || 'Parser endpoint failed');
      }

      const parseData: ParseResponse = await parseResponse.json();

      if (parseData.intent === 'not_network') {
        throw new Error('La richiesta non sembra relativa alla generazione di una rete.');
      }

      if (parseData.intent === 'incomplete') {
        const missingList = parseData.missing.join(', ');
        throw new Error(`Richiesta incompleta. Campi mancanti: ${missingList}`);
      }

      setConversationState(parseData.json);

      const generationResponse = await fetch(`${apiBaseUrl}/api/generate-pkt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(parseData.json),
      });

      if (!generationResponse.ok) {
        if (generationResponse.status >= 500) {
          throw new Error('Cannot connect to server. Make sure backend is running on port 8000.');
        }
        const errorData = await generationResponse.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.detail || `Server error: ${generationResponse.status}`);
      }

      const data: GenerateResponse = await generationResponse.json();

      if (data.success && data.pkt_download_url) {
        setResult(data);
      } else {
        throw new Error(data.error || data.message || 'Failed to generate network');
      }
    } catch (err) {
      console.error('Generation error:', err);
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Cannot connect to server. Make sure the backend is running at ' + apiBaseUrl);
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
    <>
      <SEOHead
        title="Network Generator"
        description="Generate Cisco Packet Tracer networks from natural language descriptions."
        ogUrl="https://nettrace.app/generator"
        canonicalUrl="https://nettrace.app/generator"
      />
      <div className="min-h-screen bg-slate-950 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-white mb-4">Network Generator</h1>
            <p className="text-slate-400 text-lg">
              Generate Cisco Packet Tracer networks from natural language descriptions
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <NetworkInput onGenerate={handleGenerate} isGenerating={isGenerating} />
              <PktAnalyzer onAnalysisComplete={setAnalysisResult} />

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

            <div className="space-y-6">
              {analysisResult && (
                <Card className="border-slate-800 bg-slate-900">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-amber-300">
                          <FileWarning className="h-5 w-5" />
                          PKT Diagnostic Report
                        </CardTitle>
                        <CardDescription className="mt-2 text-slate-400">
                          {analysisResult.filename || 'Uploaded file'}
                        </CardDescription>
                      </div>
                      <Badge className="bg-amber-500 text-slate-950 hover:bg-amber-500">
                        {analysisResult.issue_count} issue{analysisResult.issue_count === 1 ? '' : 's'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {analysisResult.summary && (
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-200">
                        {analysisResult.summary}
                      </div>
                    )}

                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Devices</p>
                        <p className="mt-1 text-2xl font-semibold text-white">{analysisResult.device_count}</p>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Links</p>
                        <p className="mt-1 text-2xl font-semibold text-white">{analysisResult.link_count}</p>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Findings</p>
                        <p className="mt-1 text-2xl font-semibold text-white">{analysisResult.issue_count}</p>
                      </div>
                    </div>

                    {analysisResult.issues.length === 0 ? (
                      <div className="rounded-lg border border-emerald-900 bg-emerald-950/40 p-4 text-sm text-emerald-200">
                        Nessun errore evidente trovato nel file `.pkt`.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {analysisResult.issues.map((issue, index) => (
                          <div
                            key={`${issue.code}-${index}`}
                            className={`rounded-lg border p-4 ${
                              issue.severity === 'error'
                                ? 'border-red-900 bg-red-950/30'
                                : 'border-amber-900 bg-amber-950/30'
                            }`}
                          >
                            <div className="mb-2 flex items-center justify-between gap-3">
                              <div>
                                <p className="font-semibold text-white">{issue.title}</p>
                                <p className="text-xs uppercase tracking-wide text-slate-400">{issue.code}</p>
                              </div>
                              <Badge
                                variant="secondary"
                                className={
                                  issue.severity === 'error'
                                    ? 'bg-red-500 text-white'
                                    : 'bg-amber-500 text-slate-950'
                                }
                              >
                                {issue.severity}
                              </Badge>
                            </div>
                            <p className="text-sm text-slate-200">{issue.message}</p>
                            {(issue.device || issue.interface) && (
                              <p className="mt-2 text-xs text-slate-400">
                                {[issue.device, issue.interface].filter(Boolean).join(' / ')}
                              </p>
                            )}
                            {issue.suggestion && (
                              <p className="mt-3 text-sm text-slate-300">
                                <span className="font-medium text-slate-100">Suggerimento:</span> {issue.suggestion}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {isDownloadResultData(result) ? (
                <DownloadResult data={result} />
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
    </>
  );
}
