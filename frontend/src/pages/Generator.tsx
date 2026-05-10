import { useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { getApiBaseUrl } from '@/lib/api';
import { NetworkInput, type AssistantHint, type ChatMessage } from '@/components/NetworkInput';
import { DownloadResult } from '@/components/DownloadResult';
import { SEOHead } from '@/components/SEOHead';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, FileWarning } from 'lucide-react';
import type { PktAnalysisResponse } from '@/lib/api';
import { Footer } from '@/sections/Footer';

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
  suggestedDefaults?: Record<string, unknown>;
  error?: string | null;
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
      result.subnets,
  );
}

export function Generator() {
  const { getToken } = useAuth();
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<Record<string, unknown>>({});
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'assistant-welcome',
      role: 'assistant',
      content:
        'Descrivimi la rete in linguaggio naturale. Se mancano CIDR, numero di device o protocollo, ti chiederò solo quei dati e puoi anche proseguire con i default.',
    },
  ]);
  const [pendingParse, setPendingParse] = useState<ParseResponse | null>(null);
  const [analysisResult] = useState<PktAnalysisResponse | null>(null);

  const appendChatMessage = (role: ChatMessage['role'], content: string) => {
    setChatMessages((current) => [
      ...current,
      {
        id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
      },
    ]);
  };

  const fieldLabels: Record<string, string> = {
    base_network: 'rete base in CIDR',
    routers: 'numero di router',
    switches: 'numero di switch',
    pcs: 'numero di PC',
    routing_protocol: 'protocollo di routing',
  };

  const formatMissing = (fields: string[]) => fields.map((field) => fieldLabels[field] || field).join(', ');

  const generateFromPayload = async (payload: Record<string, unknown>, token?: string | null) => {
    const apiBaseUrl = getApiBaseUrl();
    const generationResponse = await fetch(`${apiBaseUrl}/api/generate-pkt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
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
      setPendingParse(null);
      appendChatMessage(
        'assistant',
        `Configurazione completata. Genero la rete con ${String(payload.base_network || 'rete default')} e ${
          String(payload.routing_protocol || 'routing default')
        }.`,
      );
      return;
    }

    throw new Error(data.error || data.message || 'Failed to generate network');
  };

  const handleGenerate = async (description: string) => {
    setIsGenerating(true);
    setError(null);
    setResult(null);
    appendChatMessage('user', description);
    const isFollowUp = pendingParse !== null;
    const requestState = isFollowUp ? conversationState : {};

    if (!isFollowUp) {
      setConversationState({});
      setPendingParse(null);
    }

    const apiBaseUrl = getApiBaseUrl();

    try {
      const token = await getToken();
      const parseResponse = await fetch(`${apiBaseUrl}/api/parse-network-request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          user_input: description,
          current_state: requestState,
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
        setConversationState(parseData.json || {});
        setPendingParse(parseData);
        appendChatMessage(
          'assistant',
          `Mi mancano ancora: ${formatMissing(parseData.missing)}. Puoi scriverli nel prossimo messaggio oppure usare i parametri di default proposti.`,
        );
        if (parseData.error) {
          setError(parseData.error);
        }
        return;
      }

      setConversationState(parseData.json);
      setPendingParse(null);
      await generateFromPayload(parseData.json, token);
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

  const handleUseDefaults = async () => {
    if (!pendingParse) {
      return;
    }

    setIsGenerating(true);
    setError(null);
    setResult(null);

    const finalPayload = {
      ...(pendingParse.json || {}),
      ...(pendingParse.suggestedDefaults || {}),
    };

    try {
      const token = await getToken();
      setConversationState(finalPayload);
      appendChatMessage(
        'user',
        `Usa i default per: ${Object.keys(pendingParse.suggestedDefaults || {}).join(', ') || 'campi mancanti'}`,
      );
      await generateFromPayload(finalPayload, token);
    } catch (err) {
      console.error('Default generation error:', err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const assistantHint: AssistantHint | null = pendingParse
    ? {
        message: `Servono ancora ${pendingParse.missing.length} parametri per completare il JSON da inviare al server.`,
        missing: pendingParse.missing,
        suggestedDefaults: pendingParse.suggestedDefaults || {},
        onUseDefaults:
          pendingParse.suggestedDefaults && Object.keys(pendingParse.suggestedDefaults).length > 0
            ? handleUseDefaults
            : undefined,
      }
    : null;

  return (
    <>
      <SEOHead
        title="Network Generator"
        description="Generate Cisco Packet Tracer networks from natural language descriptions."
        ogUrl="https://nettrace.app/generator"
        canonicalUrl="https://nettrace.app/generator"
      />
      <div className="min-h-screen py-24 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
              Network Generator
            </h1>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto">
              Genera reti Cisco Packet Tracer da descrizioni in linguaggio naturale
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <NetworkInput
                onGenerate={handleGenerate}
                isGenerating={isGenerating}
                chatMessages={chatMessages}
                assistantHint={assistantHint}
              />

              {error && (
                <Alert variant="destructive" className="bg-red-950 border-red-900">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Errore</AlertTitle>
                  <AlertDescription className="mt-2">
                    {error}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRetry}
                      className="mt-3 w-full border-red-800 hover:bg-red-900"
                    >
                      Riprova
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

                    {analysisResult.review && (
                      <div className="space-y-4 rounded-lg border border-cyan-900 bg-cyan-950/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold text-cyan-100">Review Pro</p>
                          <Badge className="bg-cyan-500 text-slate-950 hover:bg-cyan-500">
                            {analysisResult.review.source}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-200">{analysisResult.review.overview}</p>

                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="rounded-lg border border-emerald-900 bg-emerald-950/30 p-4">
                            <p className="mb-3 font-medium text-emerald-100">Cose che vanno bene</p>
                            <ul className="space-y-2 text-sm text-emerald-50">
                              {analysisResult.review.things_correct.map((item, index) => (
                                <li key={`good-${index}`}>• {item}</li>
                              ))}
                            </ul>
                          </div>
                          <div className="rounded-lg border border-amber-900 bg-amber-950/30 p-4">
                            <p className="mb-3 font-medium text-amber-100">Cose da correggere</p>
                            <ul className="space-y-2 text-sm text-amber-50">
                              {analysisResult.review.things_to_fix.map((item, index) => (
                                <li key={`fix-${index}`}>• {item}</li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        {analysisResult.review.alignment_with_exercise && (
                          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-200">
                            <p className="mb-2 font-medium text-white">Confronto con la consegna</p>
                            <p>{analysisResult.review.alignment_with_exercise}</p>
                          </div>
                        )}
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
      <Footer />
    </>
  );
}
