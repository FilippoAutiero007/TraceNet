import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sparkles, Loader2, HelpCircle, Bookmark, X } from 'lucide-react';

interface NetworkInputProps {
  onGenerate: (description: string) => Promise<void>;
  isGenerating: boolean;
}

const DEFAULT_TEMPLATES = [
  { name: 'Small Office', description: 'Create network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing' },
  { name: 'Corporate Campus', description: 'Network with 3 buildings: Building_A (100 hosts), Building_B (50 hosts), Building_C (25 hosts) using OSPF' },
  { name: 'Data Center', description: 'Data center with DMZ (5 servers), Production (50 hosts), Management (10 hosts) using EIGRP' },
  { name: 'School Network', description: 'School network with Labs (100 hosts), Teachers (30 hosts), Admin (10 hosts), Guests (50 hosts) using RIP' },
];

const ROUTING_PROTOCOLS = ['RIP', 'OSPF', 'EIGRP', 'BGP', 'static routing'];

function loadCustomTemplates(): { name: string; description: string }[] {
  try { return JSON.parse(localStorage.getItem('nettrace_custom_templates') || '[]'); } catch { return []; }
}
function saveCustomTemplates(templates: { name: string; description: string }[]) {
  try { localStorage.setItem('nettrace_custom_templates', JSON.stringify(templates)); } catch {}
}

function getCharWarning(len: number): { text: string; color: string } | null {
  if (len > 0 && len < 20) return { text: 'Description is too short', color: 'text-amber-400' };
  if (len > 600) return { text: 'Description is very long — keep it under 600 characters for best results', color: 'text-amber-400' };
  return null;
}

export function NetworkInput({ onGenerate, isGenerating }: NetworkInputProps) {
  const [description, setDescription] = useState('');
  const [customTemplates, setCustomTemplates] = useState(loadCustomTemplates);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const allTemplates = [...DEFAULT_TEMPLATES, ...customTemplates];

  const handleTemplateClick = (text: string) => setDescription(text);

  const handleProtocolInsert = (protocol: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newText = description.slice(0, start) + protocol + description.slice(end);
    setDescription(newText);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + protocol.length, start + protocol.length);
    }, 0);
  };

  const handleSaveTemplate = () => {
    const name = prompt('Template name:');
    if (!name?.trim() || !description.trim()) return;
    const updated = [...customTemplates, { name: name.trim(), description: description.trim() }];
    setCustomTemplates(updated);
    saveCustomTemplates(updated);
  };

  const handleDeleteCustomTemplate = (idx: number) => {
    const updated = customTemplates.filter((_, i) => i !== idx);
    setCustomTemplates(updated);
    saveCustomTemplates(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim() && !isGenerating) await onGenerate(description);
  };

  const charWarning = getCharWarning(description.length);

  return (
    <TooltipProvider>
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-cyan-400">
            <Sparkles className="w-5 h-5" />
            Network Description
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Templates */}
            <div id="generator-templates" className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Quick Templates</label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <HelpCircle className="w-3.5 h-3.5 text-slate-600 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="left" className="max-w-[220px] text-xs">
                    Click a template to fill the description. You can edit it before generating.
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {DEFAULT_TEMPLATES.map((t) => (
                  <Button
                    key={t.name}
                    type="button"
                    variant="outline"
                    className="h-auto py-2.5 px-3 text-left justify-start bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200 hover:border-cyan-600 hover:text-white focus-visible:ring-2 focus-visible:ring-cyan-500"
                    onClick={() => handleTemplateClick(t.description)}
                    disabled={isGenerating}
                    aria-label={`Use template: ${t.name}`}
                  >
                    <span className="text-xs font-semibold">{t.name}</span>
                  </Button>
                ))}
                {customTemplates.map((t, i) => (
                  <div key={`custom-${i}`} className="relative">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-auto py-2.5 px-3 text-left justify-start bg-slate-800/50 hover:bg-slate-700 border-dashed border-slate-600 text-cyan-300 hover:border-cyan-500 focus-visible:ring-2 focus-visible:ring-cyan-500 pr-8"
                      onClick={() => handleTemplateClick(t.description)}
                      disabled={isGenerating}
                    >
                      <span className="text-xs font-semibold truncate">{t.name}</span>
                    </Button>
                    <button
                      type="button"
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-red-400 p-0.5"
                      onClick={() => handleDeleteCustomTemplate(i)}
                      aria-label={`Delete template ${t.name}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Textarea */}
            <div id="generator-textarea" className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="description" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Description
                </label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <HelpCircle className="w-3.5 h-3.5 text-slate-600 cursor-help" aria-label="Description help" />
                  </TooltipTrigger>
                  <TooltipContent side="left" className="max-w-[240px] text-xs">
                    Describe your network in natural language. Include: number of routers, subnets, hosts per subnet, and the routing protocol (RIP, OSPF, EIGRP, etc.).
                  </TooltipContent>
                </Tooltip>
              </div>
              <Textarea
                ref={textareaRef}
                id="description"
                placeholder="e.g., Create a network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using OSPF"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isGenerating}
                rows={5}
                className="bg-slate-800 border-slate-700 text-slate-100 placeholder:text-slate-500 resize-none focus-visible:ring-cyan-500 focus-visible:border-cyan-600"
                aria-describedby="char-info"
              />
              <div id="char-info" className="flex items-center justify-between text-xs">
                <span className={charWarning ? charWarning.color : 'text-slate-500'}>
                  {charWarning ? charWarning.text : '\u00A0'}
                </span>
                <span className={description.length > 600 ? 'text-amber-400' : 'text-slate-500'}>
                  {description.length}/600
                </span>
              </div>
            </div>

            {/* Protocol suggestions */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-500">Insert routing protocol:</span>
              <div className="flex flex-wrap gap-1.5">
                {ROUTING_PROTOCOLS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => handleProtocolInsert(p)}
                    disabled={isGenerating}
                    className="px-2 py-0.5 rounded text-xs bg-slate-800 border border-slate-700 text-cyan-300 hover:bg-slate-700 hover:border-cyan-600 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 disabled:opacity-40"
                    aria-label={`Insert ${p}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <Button
                id="generator-submit"
                type="submit"
                disabled={!description.trim() || isGenerating || description.length < 10}
                className="w-full bg-cyan-500 hover:bg-cyan-400 text-white font-semibold py-6 text-base focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                aria-label="Generate network"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" aria-hidden="true" />
                    Generating…
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-5 w-5" aria-hidden="true" />
                    Generate Network
                  </>
                )}
              </Button>
              {description.trim().length > 20 && !isGenerating && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full text-slate-500 hover:text-cyan-400 text-xs gap-1.5"
                  onClick={handleSaveTemplate}
                  aria-label="Save current description as template"
                >
                  <Bookmark className="w-3.5 h-3.5" />
                  Save as Template
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
