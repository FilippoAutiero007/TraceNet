import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowRight, Play, Activity, Shield, Zap } from 'lucide-react';
import { SignUpButton } from '@clerk/clerk-react';

export function Hero() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <section className="relative min-h-screen flex items-center justify-center bg-slate-950 overflow-hidden pt-16">
      {/* Background Grid Animation */}
      <div className="absolute inset-0 opacity-20">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Animated Particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-cyan-400/30 rounded-full animate-pulse"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 2}s`,
              animationDuration: `${2 + Math.random() * 2}s`,
            }}
          />
        ))}
      </div>

      {/* Gradient Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-8">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-cyan-400 text-sm font-medium">Simulazione di Rete Intelligente</span>
          </div>

          {/* Main Heading */}
          <h1 className="text-7xl sm:text-8xl md:text-9xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-8 tracking-tighter filter drop-shadow-[0_0_30px_rgba(6,182,212,0.5)] animate-in fade-in zoom-in duration-1000">
            NET TRACE
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            NetTrace è lo strumento automatizzato per la tracciatura e l'analisi dei pacchetti di rete.
            Simula, traccia e analizza il comportamento dei pacchetti in reti complesse.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <SignUpButton mode="modal">
              <Button
                size="lg"
                className="bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-6 text-lg group"
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
              >
                Inizia Gratuitamente
                <ArrowRight className={`w-5 h-5 ml-2 transition-transform ${isHovered ? 'translate-x-1' : ''}`} />
              </Button>
            </SignUpButton>
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg"
            >
              <Play className="w-5 h-5 mr-2" />
              Guarda la Demo
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
            {[
              { value: '10K+', label: 'Utenti Attivi' },
              { value: '50M+', label: 'Pacchetti Analizzati' },
              { value: '99.9%', label: 'Uptime' },
              { value: '4.9/5', label: 'Valutazione' },
            ].map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-slate-500 text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mt-20">
          {[
            {
              icon: Zap,
              title: 'Simulazione Real-time',
              description: 'Visualizza il flusso dei pacchetti in tempo reale con animazioni fluide.',
            },
            {
              icon: Shield,
              title: 'Analisi Sicura',
              description: 'Ambiente isolato per testare configurazioni senza rischi.',
            },
            {
              icon: Activity,
              title: 'Report Dettagliati',
              description: 'Esporta analisi in formato PCAP, JSON e CSV.',
            },
          ].map((feature, index) => (
            <div
              key={index}
              className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm hover:border-cyan-500/50 transition-colors"
            >
              <feature.icon className="w-10 h-10 text-cyan-400 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-slate-400 text-sm">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
