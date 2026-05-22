import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, AlertCircle, Upload, Loader2, Bug, Sparkles, FileX, RefreshCw, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignInButton } from '@clerk/clerk-react';
import { useAuth } from '@clerk/clerk-react';
import { Footer } from '@/sections/Footer';
import { apiClient, type PktAnalysisResponse, type UserCapabilitiesResponse } from '@/lib/api';

export function Analisi() {
  const { getToken, isSignedIn } = useAuth();
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [exerciseText, setExerciseText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<PktAnalysisResponse | null>(null);
  const [capabilities, setCapabilities] = useState<UserCapabilitiesResponse | null>(null);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(true);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let isMounted = true;

    const loadCapabilities = async () => {
      setIsLoadingCapabilities(true);
      try {
        const token = await getToken();
        const caps = await apiClient.getUserCapabilities(token);
        if (isMounted) {
          setCapabilities(caps);
        }
      } catch {
        if (isMounted) {
          setCapabilities(null);
        }
      } finally {
        if (isMounted) {
          setIsLoadingCapabilities(false);
        }
      }
    };

    void loadCapabilities();

    return () => {
      isMounted = false;
    };
  }, [getToken]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
    setAnalysisResult(null);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0] ?? null;
    if (file) {
      setSelectedFile(file);
      setError(null);
      setAnalysisResult(null);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const getErrorMessage = (err: unknown): string => {
    if (err instanceof Error) {
      const msg = err.message.toLowerCase();
      if (msg.includes('service temporarily unavailable') || msg.includes('auth_service_temporarily_unavailable')) {
        return 'Servizio di autenticazione temporaneamente non disponibile. Il server potrebbe essere in fase di avvio. Riprova tra qualche secondo.';
      }
      if (msg.includes('pro plan required')) {
        return 'Questa funzionalità richiede un piano Pro.';
      }
      if (msg.includes('authentication required') || msg.includes('invalid authentication')) {
        return 'Devi effettuare l\'accesso per utilizzare questa funzionalità.';
      }
      if (msg.includes('service unavailable') || msg.includes('503')) {
        return 'Servizio temporaneamente non disponibile. Il backend potrebbe essere in fase di avvio. Riprova tra qualche secondo.';
      }
      return err.message;
    }
    return 'Analisi del file non riuscita.';
  };

  const handleAnalyze = async () => {
    if (!selectedFile || isAnalyzing) return;

    setIsAnalyzing(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const token = await getToken();

      if (!token) {
        setError('Devi effettuare l\'accesso per analizzare un file.');
        return;
      }

      const result = await apiClient.analyzePktFile(selectedFile, {
        exerciseText,
        token,
      });
      setAnalysisResult(result);
      setRetryCount(0);
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);

      if (message.toLowerCase().includes('temporaneamente') || message.toLowerCase().includes('avvio')) {
        setRetryCount((prev) => prev + 1);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setExerciseText('');
    setError(null);
    setAnalysisResult(null);
    setRetryCount(0);
  };

  const handleDownloadPdf = async () => {
    if (!selectedFile || isDownloadingPdf) return;

    setIsDownloadingPdf(true);
    try {
      const token = await getToken();
      if (!token) {
        setError('Devi effettuare l\'accesso per scaricare il report PDF.');
        return;
      }

      const blob = await apiClient.downloadPktAnalysisPdf(selectedFile, {
        exerciseText,
        token,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      const baseName = selectedFile.name.replace(/\.pkt$/i, '') || 'network';
      anchor.href = url;
      anchor.download = `${baseName}_analysis_report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const isPro = capabilities?.can_use_pro_pkt_review ?? false;
  const isAuthenticated = capabilities?.is_authenticated ?? isSignedIn ?? false;

  if (isLoadingCapabilities) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto mb-4" />
          <p className="text-slate-400">Caricamento...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen">
        <section className="relative py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
                Analisi File .pkt
              </h1>
              <p className="text-xl text-slate-300 max-w-3xl mx-auto">
                Carica un file Packet Tracer e ottieni una review tecnica dettagliata
              </p>
            </div>

            <Card className="bg-slate-900/50 border-slate-800 p-8 text-center">
              <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Accesso richiesto
              </h2>
              <p className="text-slate-400 mb-6">
                Devi effettuare l'accesso per utilizzare la correzione avanzata dei file Packet Tracer.
              </p>
              <SignInButton mode="modal">
                <Button className="bg-cyan-500 hover:bg-cyan-600 text-white">
                  Accedi o Registrati
                </Button>
              </SignInButton>
            </Card>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  if (!isPro) {
    return (
      <div className="min-h-screen">
        <section className="relative py-24 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
                Analisi File .pkt
              </h1>
              <p className="text-xl text-slate-300 max-w-3xl mx-auto">
                Carica un file Packet Tracer e ottieni una review tecnica dettagliata
              </p>
            </div>

            <Card className="bg-slate-900/50 border-slate-800 p-8 text-center">
              <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Piano Pro richiesto
              </h2>
              <p className="text-slate-400 mb-6">
                Il tuo piano attuale non include la correzione avanzata dei file Packet Tracer importati.
              </p>
              <Button
                className="bg-cyan-500 hover:bg-cyan-600 text-white"
                onClick={() => navigate('/pricing')}
              >
                Aggiorna al piano Pro
              </Button>
            </Card>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <section className="relative py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
              Analisi File .pkt
            </h1>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto">
              Carica un file Packet Tracer e ottieni una review tecnica dettagliata
            </p>
          </div>

          {!analysisResult ? (
            <Card className="bg-slate-900/50 border-slate-800 p-8">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-2">
                  Seleziona un file
                </h2>
                <p className="text-slate-400 text-sm">
                  Formato supportato: <span className="text-cyan-400">.pkt</span> (Packet Tracer)
                </p>
              </div>

              <div
                className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-cyan-500/50 transition-colors cursor-pointer"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <Upload className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
                {selectedFile ? (
                  <>
                    <p className="text-slate-200 font-medium mb-1">{selectedFile.name}</p>
                    <p className="text-slate-500 text-sm">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                  </>
                ) : (
                  <>
                    <p className="text-slate-300 mb-2">
                      Trascina il file qui o clicca per selezionare
                    </p>
                    <p className="text-slate-500 text-sm">
                      Massimo 10MB
                    </p>
                  </>
                )}
                <input
                  id="file-input"
                  type="file"
                  accept=".pkt"
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </div>

              {selectedFile && (
                <div className="mt-4 flex items-center gap-2">
                  <Badge variant="secondary" className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
                    File selezionato
                  </Badge>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReset();
                    }}
                    className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    Rimuovi
                  </button>
                </div>
              )}

              <div className="mt-6">
                <label className="block text-white font-medium mb-2">
                  Testo esercizio opzionale
                </label>
                <textarea
                  className="w-full h-32 bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  placeholder="Puoi lasciare solo il file oppure aggiungere anche la consegna: es. 'realizza due VLAN, routing OSPF e DHCP centralizzato...'"
                  value={exerciseText}
                  onChange={(e) => setExerciseText(e.target.value)}
                />
                <div className="flex items-center gap-2 text-slate-500 text-sm mt-2">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Modalità supportate: solo file oppure file + testo dell'esercizio</span>
                </div>
              </div>

              {error && (
                <div className="mt-4 flex items-start gap-3 bg-red-950/50 border border-red-900 rounded-lg p-4">
                  <XCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-red-200 font-medium text-sm mb-1">Errore</p>
                    <p className="text-red-300 text-sm">{error}</p>
                    {retryCount > 0 && retryCount < 3 && (
                      <button
                        onClick={handleAnalyze}
                        className="mt-2 flex items-center gap-1 text-cyan-400 hover:text-cyan-300 text-sm transition-colors"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Riprova ora
                      </button>
                    )}
                  </div>
                </div>
              )}

              <Button
                className="w-full mt-6 bg-cyan-500 hover:bg-cyan-600 text-white py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleAnalyze}
                disabled={!selectedFile || isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Analisi in corso...
                  </>
                ) : (
                  <>
                    <Bug className="w-5 h-5 mr-2" />
                    Correggi file
                  </>
                )}
              </Button>
            </Card>
          ) : (
            <div className="space-y-6">
              <Card className="bg-slate-900/50 border-slate-800 p-8">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">Risultati Analisi</h2>
                    <p className="text-slate-400 text-sm">{analysisResult.filename}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      onClick={handleDownloadPdf}
                      disabled={!selectedFile || isDownloadingPdf}
                      className="border-cyan-800 text-cyan-300 hover:bg-cyan-950/40"
                    >
                      {isDownloadingPdf ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Creo PDF...
                        </>
                      ) : (
                        <>
                          <FileText className="w-4 h-4 mr-2" />
                          Scarica PDF
                        </>
                      )}
                    </Button>
                    <Button variant="outline" onClick={handleReset} className="border-slate-700 text-slate-300 hover:bg-slate-800">
                      Nuova analisi
                    </Button>
                  </div>
                </div>

                {analysisResult.success ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                        <p className="text-3xl font-bold text-cyan-400">{analysisResult.device_count}</p>
                        <p className="text-slate-400 text-sm">Dispositivi</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                        <p className="text-3xl font-bold text-blue-400">{analysisResult.link_count}</p>
                        <p className="text-slate-400 text-sm">Connessioni</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center col-span-2 sm:col-span-1">
                        <p className={`text-3xl font-bold ${analysisResult.issue_count === 0 ? 'text-green-400' : 'text-amber-400'}`}>
                          {analysisResult.issue_count}
                        </p>
                        <p className="text-slate-400 text-sm">Problemi</p>
                      </div>
                    </div>

                    {analysisResult.summary && (
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h3 className="text-white font-medium mb-2">Riepilogo</h3>
                        <p className="text-slate-300 text-sm">{analysisResult.summary}</p>
                      </div>
                    )}

                    {analysisResult.issues.length > 0 && (
                      <div>
                        <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-400" />
                          Problemi rilevati
                        </h3>
                        <div className="space-y-3">
                          {analysisResult.issues.map((issue, index) => (
                            <div
                              key={index}
                              className={`rounded-lg p-4 border ${
                                issue.severity === 'error'
                                  ? 'bg-red-950/30 border-red-900/50'
                                  : 'bg-amber-950/30 border-amber-900/50'
                              }`}
                            >
                              <div className="flex items-start gap-3">
                                {issue.severity === 'error' ? (
                                  <XCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                                ) : (
                                  <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                                )}
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-white font-medium text-sm">{issue.title}</span>
                                    <Badge
                                      variant="outline"
                                      className={`text-xs ${
                                        issue.severity === 'error'
                                          ? 'border-red-800 text-red-400'
                                          : 'border-amber-800 text-amber-400'
                                      }`}
                                    >
                                      {issue.severity === 'error' ? 'Errore' : 'Warning'}
                                    </Badge>
                                  </div>
                                  <p className="text-slate-300 text-sm">{issue.message}</p>
                                  {issue.device && (
                                    <p className="text-slate-500 text-xs mt-1">Dispositivo: {issue.device}</p>
                                  )}
                                  {issue.interface && (
                                    <p className="text-slate-500 text-xs mt-1">Interfaccia: {issue.interface}</p>
                                  )}
                                  {issue.suggestion && (
                                    <p className="text-cyan-400 text-xs mt-1">Suggerimento: {issue.suggestion}</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {analysisResult.issue_count === 0 && (
                      <div className="flex items-center gap-3 bg-green-950/30 border border-green-900/50 rounded-lg p-4">
                        <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0" />
                        <div>
                          <p className="text-green-200 font-medium">Nessun problema rilevato</p>
                          <p className="text-green-300/70 text-sm">La topologia sembra corretta</p>
                        </div>
                      </div>
                    )}

                    {analysisResult.review && (
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h3 className="text-white font-medium mb-3 flex items-center gap-2">
                          <Bug className="w-4 h-4 text-amber-400" />
                          Review AI
                          <Badge variant="outline" className="border-amber-800 text-amber-400 text-xs">
                            {analysisResult.review.source === 'mistral' ? 'Mistral AI' : 'Fallback'}
                          </Badge>
                        </h3>
                        <p className="text-slate-300 text-sm mb-4">{analysisResult.review.overview}</p>

                        {analysisResult.review.things_correct.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-green-400 font-medium text-sm mb-2 flex items-center gap-2">
                              <CheckCircle className="w-3.5 h-3.5" />
                              Punti corretti
                            </h4>
                            <ul className="space-y-1">
                              {analysisResult.review.things_correct.map((item, i) => (
                                <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                                  <span className="text-green-500 mt-1">•</span>
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {analysisResult.review.things_to_fix.length > 0 && (
                          <div>
                            <h4 className="text-red-400 font-medium text-sm mb-2 flex items-center gap-2">
                              <XCircle className="w-3.5 h-3.5" />
                              Da correggere
                            </h4>
                            <ul className="space-y-1">
                              {analysisResult.review.things_to_fix.map((item, i) => (
                                <li key={i} className="text-slate-300 text-sm flex items-start gap-2">
                                  <span className="text-red-500 mt-1">•</span>
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {analysisResult.review.alignment_with_exercise && (
                          <div className="mt-4 pt-4 border-t border-slate-700">
                            <h4 className="text-cyan-400 font-medium text-sm mb-2">Allineamento con l'esercizio</h4>
                            <p className="text-slate-300 text-sm">{analysisResult.review.alignment_with_exercise}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {analysisResult.remediation_steps && analysisResult.remediation_steps.length > 0 && (
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h3 className="text-white font-medium mb-3">Passi consigliati per correggere il file</h3>
                        <ol className="space-y-2">
                          {analysisResult.remediation_steps.map((step, index) => (
                            <li key={index} className="text-slate-300 text-sm flex items-start gap-3">
                              <span className="text-cyan-400 font-semibold min-w-5">{index + 1}.</span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {analysisResult.report && (
                      <div className="bg-slate-800/30 rounded-lg p-4">
                        <h3 className="text-white font-medium mb-2">Report completo</h3>
                        <pre className="text-slate-300 text-sm whitespace-pre-wrap font-mono bg-slate-950/50 rounded p-3 max-h-64 overflow-y-auto">
                          {analysisResult.report}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-3 bg-red-950/30 border border-red-900/50 rounded-lg p-6">
                    <FileX className="w-8 h-8 text-red-400 flex-shrink-0" />
                    <div>
                      <p className="text-red-200 font-medium">Analisi fallita</p>
                      <p className="text-red-300/70 text-sm">{analysisResult.error || 'Impossibile analizzare il file'}</p>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          )}

          <Card className="bg-slate-900/50 border-slate-800 p-8 mt-8">
            <h3 className="text-xl font-bold text-white mb-6">
              Cosa include la correzione:
            </h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                <span className="text-slate-300">
                  Elenco delle correzioni necessarie
                </span>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                <span className="text-slate-300">
                  Punti già corretti
                </span>
              </div>
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                <span className="text-slate-300">
                  Confronto opzionale con la consegna dell'esercizio
                </span>
              </div>
            </div>
          </Card>
        </div>
      </section>
      <Footer />
    </div>
  );
}
