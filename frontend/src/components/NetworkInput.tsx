import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Sparkles, Loader2, MessageSquareText, Bot, User, WandSparkles } from 'lucide-react';

interface NetworkInputProps {
  onGenerate: (description: string) => Promise<void>;
  isGenerating: boolean;
  chatMessages?: ChatMessage[];
  assistantHint?: AssistantHint | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface AssistantHint {
  message: string;
  missing: string[];
  suggestedDefaults?: Record<string, unknown>;
  onUseDefaults?: () => void;
}

const TEMPLATES = [
  {
    name: 'Small Office',
    description: 'Create network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing',
  },
  {
    name: 'Corporate Campus',
    description: 'Network with 3 buildings: Building_A (100 hosts), Building_B (50 hosts), Building_C (25 hosts) using OSPF',
  },
  {
    name: 'Data Center',
    description: 'Data center with DMZ (5 servers), Production (50 hosts), Management (10 hosts) using EIGRP',
  },
  {
    name: 'School Network',
    description: 'School network with Labs (100 hosts), Teachers (30 hosts), Admin (10 hosts), Guests (50 hosts) using RIP',
  },
];

export function NetworkInput({
  onGenerate,
  isGenerating,
  chatMessages = [],
  assistantHint = null,
}: NetworkInputProps) {
  const [description, setDescription] = useState('');

  const handleTemplateClick = (templateDescription: string) => {
    setDescription(templateDescription);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim() && !isGenerating) {
      const message = description;
      setDescription('');
      await onGenerate(message);
    }
  };

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-cyan-500">
          <Sparkles className="w-5 h-5" />
          Chat Generatore
        </CardTitle>
        <CardDescription className="text-slate-400">
          Descrivi la rete. Se mancano dati, l&apos;assistant ti chiederà solo i parametri necessari o ti farà usare i default.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
              <MessageSquareText className="h-4 w-4 text-cyan-400" />
              Conversazione
            </div>
            <div className="space-y-3">
              {chatMessages.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-500">
                  Inizia con una richiesta come: &quot;Crea una rete 10.0.0.0/24 con 2 router e OSPF&quot;.
                </div>
              ) : (
                chatMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 rounded-xl border p-3 ${
                      message.role === 'assistant'
                        ? 'border-cyan-950 bg-cyan-950/20'
                        : 'border-slate-800 bg-slate-900'
                    }`}
                  >
                    <div className="mt-0.5">
                      {message.role === 'assistant' ? (
                        <Bot className="h-4 w-4 text-cyan-400" />
                      ) : (
                        <User className="h-4 w-4 text-slate-300" />
                      )}
                    </div>
                    <p className="text-sm leading-6 text-slate-100">{message.content}</p>
                  </div>
                ))
              )}
            </div>

            {assistantHint && (
              <div className="mt-3 rounded-xl border border-amber-900/80 bg-amber-950/30 p-4">
                <p className="text-sm font-medium text-amber-100">{assistantHint.message}</p>
                {assistantHint.missing.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {assistantHint.missing.map((field) => (
                      <Badge key={field} variant="secondary" className="bg-slate-800 text-slate-200">
                        {field}
                      </Badge>
                    ))}
                  </div>
                )}
                {assistantHint.suggestedDefaults && Object.keys(assistantHint.suggestedDefaults).length > 0 && (
                  <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-300">
                    Default proposti: {Object.entries(assistantHint.suggestedDefaults)
                      .map(([key, value]) => `${key}=${String(value)}`)
                      .join(', ')}
                  </div>
                )}
                {assistantHint.onUseDefaults && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={assistantHint.onUseDefaults}
                    disabled={isGenerating}
                    className="mt-3 border-amber-700 bg-amber-500/10 text-amber-100 hover:bg-amber-500/20"
                  >
                    <WandSparkles className="mr-2 h-4 w-4" />
                    Usa parametri di default
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Template Buttons */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Template rapidi</label>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((template) => (
                <Button
                  key={template.name}
                  type="button"
                  variant="outline"
                  className="h-auto py-3 px-4 text-left justify-start bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200"
                  onClick={() => handleTemplateClick(template.description)}
                  disabled={isGenerating}
                >
                  <div className="flex flex-col items-start gap-1">
                    <span className="font-semibold text-sm">{template.name}</span>
                  </div>
                </Button>
              ))}
            </div>
          </div>

          {/* Textarea */}
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium text-slate-300">
              Messaggio
            </label>
            <Textarea
              id="description"
              placeholder="Scrivi la richiesta iniziale oppure rispondi ai dati mancanti, ad esempio: usa 20 pc e lascia il routing statico"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isGenerating}
              rows={6}
              className="bg-slate-800 border-slate-700 text-slate-100 placeholder:text-slate-500 resize-none"
            />
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{description.length} characters</span>
            </div>
          </div>

          {/* Generate Button */}
          <Button
            type="submit"
            disabled={!description.trim() || isGenerating}
            className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-6 text-base"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Elaborazione...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-5 w-5" />
                Invia al generatore
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
