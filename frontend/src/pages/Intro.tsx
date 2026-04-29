import { ParticleEffect } from '@/components/ParticleEffect';
import { Button } from '@/components/ui/button';
import { ArrowRight, BookOpen, Lightbulb, Target } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Intro() {
  const navigate = useNavigate();

  return ( 
    <div className="min-h-screen bg-black flex flex-col">
      {/* Hero Section with Particle Effect */}
      <section className="relative flex-1 flex items-center justify-center overflow-hidden">
        <ParticleEffect />
        
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="mb-8">
            <h1 className="text-6xl sm:text-7xl md:text-8xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6 tracking-tighter">
              TRACENET
            </h1>
            <p className="text-2xl sm:text-3xl text-cyan-400 font-semibold mb-4">
              Benvenuto nel Futuro dell'Analisi di Rete
            </p>
          </div>

          <div className="max-w-2xl mx-auto mb-12">
            <p className="text-lg text-slate-300 leading-relaxed">
              TraceNet è una piattaforma all'avanguardia che combina intelligenza artificiale e 
              simulazione avanzata per fornire analisi di rete senza precedenti. 
              Progettata per professionisti e aziende che richiedono il massimo dalla propria infrastruttura di rete.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              className="bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-6 text-lg"
              onClick={() => navigate('/features')}
            >
              Scopri le Funzionalità
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg"
              onClick={() => navigate('/')}
            >
              Torna alla Home
            </Button>
          </div>
        </div>
      </section>

      {/* Key Principles */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            I Nostri Principi Fondamentali
          </h2>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 transition-colors">
              <div className="w-16 h-16 bg-cyan-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Target className="w-8 h-8 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-4">Precisione Assoluta</h3>
              <p className="text-slate-400">
                Ogni pacchetto viene analizzato con accuratezza millimetrica per garantire risultati affidabili.
              </p>
            </div>

            <div className="text-center p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 transition-colors">
              <div className="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Lightbulb className="w-8 h-8 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-4">Innovazione Continua</h3>
              <p className="text-slate-400">
                Sviluppiamo costantemente nuove tecnologie per rimanere all'avanguardia nell'analisi di rete.
              </p>
            </div>

            <div className="text-center p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 transition-colors">
              <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <BookOpen className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-4">Conoscenza Condivisa</h3>
              <p className="text-slate-400">
                Crediamo nella democratizzazione dell'analisi di rete attraverso strumenti intuitivi e accessibili.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
