import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '@/config';
import { NetworkInput } from '@/components/NetworkInput';
import { DownloadResult } from '@/components/DownloadResult';
import { GeneratorTour } from '@/components/GeneratorTour';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AlertCircle, ChevronLeft, ServerCrash, AlertTriangle, Clock, RotateCcw, Sparkles, LogIn } from 'lucide-react';
import { useGenerationHistory } from '@/hooks/useGenerationHistory';
import { formatDistanceToNow } from 'date-fns';
import { motion, AnimatePresence, type Easing } from 'framer-motion';
import { useUser } from '@clerk/clerk-react';
import { useLanguage } from '@/context/LanguageContext';

interface SubnetInfo { name: string; network: string; gateway: string; usable_hosts: number; }
interface ConfigSummary { base_network: string; subnets_count: number; routers: number; switches: number; pcs: number; routing_protocol: string; }
interface GenerateResponse { success: boolean; message?: string; error?: string; pkt_download_url?: string; xml_download_url?: string; config_summary?: ConfigSummary; subnets?: SubnetInfo[]; }
interface ParseResponse { intent: 'not_network' | 'incomplete' | 'complete'; missing: string[]; json: Record<string, unknown>; }

type Step = 'idle' | 'parsing' | 'calculating' | 'generating' | 'done' | 'error';

interface AppError {
  type: 'network' | 'invalid_input' | 'not_network' | 'incomplete' | 'rate_limit' | 'server' | 'unknown';
  title: string;
  message: string;
  hint?: string;
}

function categorizeError(err: unknown, status?: number): AppError {
  if (err instanceof TypeError && err.message.includes('fetch')) {
    return { type: 'network', title: 'Backend Unreachable', message: 'Cannot connect to the server.', hint: 'Make sure the backend is running, then try again.' };
  }
  if (status === 429) {
    return { type: 'rate_limit', title: 'Too Many Requests', message: 'You have exceeded the rate limit.', hint: 'Please wait a few minutes before trying again.' };
  }
  if (status && status >= 500) {
    return { type: 'server', title: 'Server Error', message: `The server returned an error (${status}).`, hint: 'Try again later or check the server status.' };
  }
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes('not_network') || msg.includes('non sembra')) {
    return { type: 'not_network', title: 'Not a Network Request', message: 'Your description does not seem to be about a network.', hint: 'Try describing the routers, switches, and subnets you want.' };
  }
  if (msg.includes('incomplete') || msg.includes('mancanti') || msg.includes('missing')) {
    return { type: 'incomplete', title: 'Incomplete Description', message: msg, hint: 'Add missing details: number of hosts per subnet, routing protocol, or network address.' };
  }
  return { type: 'unknown', title: 'Unexpected Error', message: msg, hint: 'Check your description and try again. If the issue persists, contact support.' };
}

const errorIcon: Record<AppError['type'], React.ElementType> = {
  network: ServerCrash, server: ServerCrash, rate_limit: Clock,
  invalid_input: AlertTriangle, not_network: AlertTriangle, incomplete: AlertTriangle, unknown: AlertCircle,
};

const STEPS: { key: Step; label: string }[] = [
  { key: 'parsing', label: 'Parse' },
  { key: 'calculating', label: 'Calculate' },
  { key: 'generating', label: 'Generate' },
];

function StepProgress({ current }: { current: Step }) {
  const stepIndex = STEPS.findIndex((s) => s.key === current);
  return (
    <div className="flex items-center gap-0 mb-6" role="status" aria-label={`Generation step: ${current}`}>
      {STEPS.map((s, i) => {
        const done = current === 'done' || (stepIndex > i);
        const active = stepIndex === i;
        return (
          <div key={s.key} className="flex items-center flex-1">
            <motion.div 
              className="flex flex-col items-center gap-1"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.1 }}
            >
              <motion.div 
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
                  done ? 'bg-cyan-500 border-cyan-500 text-white' :
                  active ? 'bg-cyan-500/20 border-cyan-400 text-cyan-400 animate-pulse' :
                  'bg-slate-800 border-slate-700 text-slate-500'
                }`}
                whileHover={{ scale: 1.1 }}
              >{i + 1}</motion.div>
              <span className={`text-[10px] font-medium ${done || active ? 'text-cyan-400' : 'text-slate-500'}`}>{s.label}</span>
            </motion.div>
            {i < STEPS.length - 1 && (
              <motion.div 
                className={`flex-1 h-0.5 mx-1 mb-4 transition-all ${done ? 'bg-cyan-500' : 'bg-slate-700'}`}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: done ? 1 : 0 }}
                transition={{ delay: i * 0.1 + 0.2 }}
                style={{ transformOrigin: 'left' }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function Generator() {
  const { t } = useLanguage();
  const { isSignedIn } = useUser();
  const [step, setStep] = useState<Step>('idle');
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<AppError | null>(null);
  const [lastDescription, setLastDescription] = useState('');
  const [generatedAt, setGeneratedAt] = useState<number | undefined>();
  const { history, addEntry } = useGenerationHistory();

  // Check authentication
  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 flex items-center justify-center px-4">
        <motion.div 
          className="text-center max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="w-16 h-16 bg-cyan-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <LogIn className="w-8 h-8 text-cyan-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-4">
            {t('generator.authRequired')}
          </h1>
          <p className="text-slate-400 mb-8">
            {t('generator.loginPrompt')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              asChild
              className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white"
            >
              <a href="/sign-in">
                {t('generator.signIn')}
              </a>
            </Button>
            <Button 
              asChild
              variant="outline"
              className="border-cyan-500 text-cyan-400 hover:bg-cyan-500/10"
            >
              <a href="/sign-up">
                {t('generator.signUp')}
              </a>
            </Button>
          </div>
        </motion.div>
      </div>
    );
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5, ease: "easeOut" as Easing },
    },
  };

  const doGenerate = useCallback(async (description: string) => {
    setStep('parsing');
    setError(null);
    setResult(null);
    setLastDescription(description);

    try {
      const parseRes = await fetch(`${API_BASE_URL}/api/parse-network-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: description, current_state: {} }),
      });
      if (!parseRes.ok) {
        const body = await parseRes.json().catch(() => ({}));
        throw Object.assign(new Error(body.error || body.detail || 'Parser failed'), { status: parseRes.status });
      }
      const parseData: ParseResponse = await parseRes.json();
      if (parseData.intent === 'not_network') throw new Error('not_network');
      if (parseData.intent === 'incomplete') throw new Error(`incomplete: missing ${parseData.missing.join(', ')}`);

      setStep('calculating');
      await new Promise((r) => setTimeout(r, 400));

      setStep('generating');
      const genRes = await fetch(`${API_BASE_URL}/api/generate-pkt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parseData.json),
      });
      if (!genRes.ok) {
        const body = await genRes.json().catch(() => ({}));
        throw Object.assign(new Error(body.error || body.detail || `Server error ${genRes.status}`), { status: genRes.status });
      }
      const data: GenerateResponse = await genRes.json();
      if (!data.success || !data.pkt_download_url) throw new Error(data.error || 'Generation failed');

      const ts = Date.now();
      setResult(data);
      setGeneratedAt(ts);
      setStep('done');
      addEntry(description, data);
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      setError(categorizeError(err, status));
      setStep('error');
    }
  }, [addEntry]);

  const handleGenerate = useCallback((desc: string) => doGenerate(desc), [doGenerate]);
  const handleRegenerate = useCallback(() => { if (lastDescription) doGenerate(lastDescription); }, [lastDescription, doGenerate]);
  const handleRetry = () => { setError(null); setStep('idle'); setResult(null); };

  const isGenerating = step === 'parsing' || step === 'calculating' || step === 'generating';

  return (
    <motion.div 
      className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 pt-20 pb-12 px-4"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <div className="max-w-7xl mx-auto">
        {/* Header row */}
        <motion.div variants={itemVariants} className="flex items-center justify-between mb-8">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-cyan-400 transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500 rounded"
            aria-label="Back to home"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <GeneratorTour />
        </motion.div>

        {/* Title */}
        <motion.div variants={itemVariants} className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/25 mb-4">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="text-cyan-400 text-xs font-medium">AI-Powered</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 tracking-tight">Cisco Network Generator</h1>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            Describe your network — get a <span className="text-cyan-400 font-semibold">.pkt</span> file ready for Cisco Packet Tracer.
          </p>
        </motion.div>

        {/* Step progress (visible while generating or done) */}
        <AnimatePresence>
          {step !== 'idle' && step !== 'error' && (
            <motion.div 
              className="max-w-xs mx-auto mb-6"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <StepProgress current={step} />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Input */}
          <motion.div variants={itemVariants} className="space-y-4">
            <NetworkInput onGenerate={handleGenerate} isGenerating={isGenerating} />
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <Alert className="bg-red-950/60 border border-red-900/80 rounded-xl">
                    <div className="flex items-start gap-3">
                      {(() => { const Icon = errorIcon[error.type]; return <Icon className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" aria-hidden="true" />; })()}
                      <div className="flex-1 min-w-0">
                        <AlertTitle className="font-semibold text-red-300">{error.title}</AlertTitle>
                        <AlertDescription className="mt-1 text-red-400 text-sm">{error.message}</AlertDescription>
                        {error.hint && <p className="mt-1 text-slate-400 text-xs">{error.hint}</p>}
                        <div className="flex gap-2 mt-3">
                          <Button variant="outline" size="sm" onClick={handleRetry} className="border-red-800 text-red-300 hover:bg-red-900 text-xs">
                            Try Again
                          </Button>
                          <a href="#" className="text-xs text-slate-500 hover:text-cyan-400 self-center underline">View FAQ</a>
                        </div>
                      </div>
                    </div>
                  </Alert>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Right: Result */}
          <motion.div id="generator-result" variants={itemVariants} className="space-y-4">
            <AnimatePresence mode="wait">
              {result && result.success && result.config_summary && result.subnets ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5 }}
                >
                  <DownloadResult
                    data={result as Parameters<typeof DownloadResult>[0]['data']}
                    generatedAt={generatedAt}
                    onRegenerate={handleRegenerate}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-full min-h-[420px] bg-gradient-to-br from-slate-900/50 to-slate-800/30 rounded-2xl border border-dashed border-slate-700"
                >
                  <div className="text-center p-10">
                    <div className="mx-auto w-14 h-14 mb-4 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-700 flex items-center justify-center">
                      <svg className="w-7 h-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    {isGenerating ? (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-2"
                      >
                        <p className="text-slate-300 font-semibold text-base mb-1">Generating your network…</p>
                        <p className="text-slate-500 text-sm">This may take a few seconds</p>
                      </motion.div>
                    ) : (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="space-y-2"
                      >
                        <p className="text-slate-300 font-semibold text-base mb-1">Your network will appear here</p>
                        <p className="text-slate-500 text-sm">Enter a description on the left to get started</p>
                      </motion.div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* History */}
        <AnimatePresence>
          {history.length > 0 && (
            <motion.div 
              className="mt-10"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ delay: 0.3 }}
            >
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Recent Generations</h2>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {history.map((entry, index) => (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-xl p-3.5 space-y-2 hover:border-cyan-500/40 transition-all duration-300"
                  >
                    <p className="text-slate-300 text-xs line-clamp-2 leading-relaxed">{entry.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600 text-xs flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDistanceToNow(entry.timestamp, { addSuffix: true })}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs text-cyan-400 hover:text-cyan-300 px-2 gap-1"
                        onClick={() => doGenerate(entry.description)}
                        aria-label="Regenerate this entry"
                      >
                        <RotateCcw className="w-3 h-3" />
                        Rerun
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
