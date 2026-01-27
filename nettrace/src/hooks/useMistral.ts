import { useState, useCallback } from 'react';
import { Mistral } from '@mistralai/mistralai';

const mistralClient = new Mistral({
  apiKey: import.meta.env.VITE_MISTRAL_API_KEY,
});

export function useMistral() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeNetwork = useCallback(async (networkConfig: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await mistralClient.chat.complete({
        model: 'mistral-tiny',
        messages: [
          {
            role: 'system',
            content: 'Sei un esperto di networking. Analizza la configurazione di rete fornita e suggerisci ottimizzazioni.',
          },
          {
            role: 'user',
            content: `Analizza questa configurazione di rete e suggerisci miglioramenti: ${networkConfig}`,
          },
        ],
      });
      
      return response.choices?.[0]?.message?.content || 'Nessuna risposta';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const explainPacket = useCallback(async (packetData: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await mistralClient.chat.complete({
        model: 'mistral-tiny',
        messages: [
          {
            role: 'system',
            content: 'Spiega in modo semplice e chiaro il comportamento dei pacchetti di rete.',
          },
          {
            role: 'user',
            content: `Spiega questo pacchetto di rete: ${packetData}`,
          },
        ],
      });
      
      return response.choices?.[0]?.message?.content || 'Nessuna risposta';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { analyzeNetwork, explainPacket, isLoading, error };
}
