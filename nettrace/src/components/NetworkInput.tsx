import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Sparkles, Loader2 } from 'lucide-react';

interface NetworkInputProps {
  onGenerate: (description: string) => Promise<void>;
  isGenerating: boolean;
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

export function NetworkInput({ onGenerate, isGenerating }: NetworkInputProps) {
  const [description, setDescription] = useState('');

  const handleTemplateClick = (templateDescription: string) => {
    setDescription(templateDescription);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim() && !isGenerating) {
      await onGenerate(description);
    }
  };

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-cyan-500">
          <Sparkles className="w-5 h-5" />
          Network Description
        </CardTitle>
        <CardDescription className="text-slate-400">
          Describe your network in natural language or choose a template
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Template Buttons */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Quick Templates:</label>
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
              Network Description:
            </label>
            <Textarea
              id="description"
              placeholder="e.g., Create a network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing"
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
                Generating Network...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-5 w-5" />
                Generate Network
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
