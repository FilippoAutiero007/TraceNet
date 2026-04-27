import { useState } from 'react';
import { AlertTriangle, Bug, FileUp, Loader2, Lock, Sparkles } from 'lucide-react';

import { apiClient, type PktAnalysisResponse, type UserCapabilitiesResponse } from '@/lib/api';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

interface PktAnalyzerProps {
  onAnalysisComplete: (result: PktAnalysisResponse | null) => void;
  capabilities: UserCapabilitiesResponse | null;
  getToken: () => Promise<string | null>;
}

export function PktAnalyzer({ onAnalysisComplete, capabilities, getToken }: PktAnalyzerProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [exerciseText, setExerciseText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canUseProReview = Boolean(capabilities?.can_use_pro_pkt_review);
  const isSignedIn = Boolean(capabilities?.is_authenticated);

  const handleAnalyze = async () => {
    if (!selectedFile || isAnalyzing || !canUseProReview) {
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    onAnalysisComplete(null);

    try {
      const token = await getToken();
      const result = await apiClient.analyzePktFile(selectedFile, {
        exerciseText,
        token,
      });
      onAnalysisComplete(result);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Analisi del file non riuscita.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-amber-400">
          <Bug className="w-5 h-5" />
          Pro PKT Review
        </CardTitle>
        <CardDescription className="text-slate-400">
          Gli utenti Pro possono caricare un file `.pkt` e ottenere una review tecnica con elenco delle correzioni, punti già corretti e confronto opzionale con la consegna dell'esercizio.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!canUseProReview && (
          <Alert className="border-amber-900 bg-amber-950/40 text-amber-100">
            <Lock className="h-4 w-4" />
            <AlertTitle>Funzione riservata al piano Pro</AlertTitle>
            <AlertDescription>
              {isSignedIn
                ? 'Il tuo piano attuale non include la correzione avanzata dei file Packet Tracer importati.'
                : 'Accedi e attiva il piano Pro per sbloccare la correzione avanzata dei file Packet Tracer importati.'}
            </AlertDescription>
          </Alert>
        )}

        <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-950/60 px-6 py-8 text-center transition hover:border-amber-500/50 hover:bg-slate-950">
          <FileUp className="mb-3 h-8 w-8 text-slate-400" />
          <span className="text-sm font-medium text-slate-200">
            {selectedFile ? selectedFile.name : 'Seleziona un file Packet Tracer'}
          </span>
          <span className="mt-1 text-xs text-slate-500">Formato supportato: `.pkt`</span>
          <input
            type="file"
            accept=".pkt"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
              setError(null);
            }}
          />
        </label>

        {selectedFile && (
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/70 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-200">{selectedFile.name}</p>
              <p className="text-xs text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
            </div>
            <Badge variant="secondary" className="bg-slate-800 text-slate-200">
              Upload pronto
            </Badge>
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="pkt-exercise" className="text-sm font-medium text-slate-300">
            Testo esercizio opzionale
          </label>
          <Textarea
            id="pkt-exercise"
            value={exerciseText}
            onChange={(event) => setExerciseText(event.target.value)}
            disabled={isAnalyzing || !canUseProReview}
            rows={5}
            className="bg-slate-800 border-slate-700 text-slate-100 placeholder:text-slate-500 resize-none"
            placeholder="Puoi lasciare solo il .pkt oppure aggiungere anche la consegna: es. 'realizza due VLAN, routing OSPF e DHCP centralizzato...'"
          />
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Modalità supportate: solo `.pkt` oppure `.pkt` + testo dell'esercizio.</span>
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="bg-red-950 border-red-900">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Analisi non riuscita</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button
          type="button"
          disabled={!selectedFile || isAnalyzing || !canUseProReview}
          onClick={handleAnalyze}
          className="w-full bg-amber-500 text-slate-950 hover:bg-amber-400"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Analisi in corso...
            </>
          ) : (
            <>
              <Bug className="mr-2 h-5 w-5" />
              Correggi file .pkt
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
