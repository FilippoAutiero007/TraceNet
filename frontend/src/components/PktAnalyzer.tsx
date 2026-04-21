import { useState } from 'react';
import { AlertTriangle, Bug, FileUp, Loader2 } from 'lucide-react';

import { apiClient, type PktAnalysisResponse } from '@/lib/api';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface PktAnalyzerProps {
  onAnalysisComplete: (result: PktAnalysisResponse | null) => void;
}

export function PktAnalyzer({ onAnalysisComplete }: PktAnalyzerProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!selectedFile || isAnalyzing) {
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    onAnalysisComplete(null);

    try {
      const result = await apiClient.analyzePktFile(selectedFile);
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
          PKT Debugger
        </CardTitle>
        <CardDescription className="text-slate-400">
          Carica un file `.pkt` e ottieni un report sugli errori di rete: gateway mancanti, subnet incoerenti, DHCP, IP duplicati e possibili problemi VLSM.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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

        {error && (
          <Alert variant="destructive" className="bg-red-950 border-red-900">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Analisi non riuscita</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Button
          type="button"
          disabled={!selectedFile || isAnalyzing}
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
              Analizza file .pkt
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
