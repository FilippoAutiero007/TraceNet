import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowRight, Activity, Zap, Brain, AlertTriangle, Github } from 'lucide-react';

import { ParticleEffect } from '@/components/ParticleEffect';

const HERO_PARTICLES = Array.from({ length: 30 }, (_, i) => {
  const normalized = (salt: number) => {
    const value = Math.sin((i + 1) * 12.9898 + salt * 78.233) * 43758.5453;
    return value - Math.floor(value);
  };

  return {
    baseX: normalized(1) * 100,
    baseY: normalized(2) * 100,
    size: normalized(3) * 3 + 1,
    duration: normalized(4) * 4 + 2,
    opacity: 0.3 + normalized(5) * 0.4,
    delay: normalized(6) * 2,
    key: i,
  };
});

export function Hero() {
  const [isHovered, setIsHovered] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const heroRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        setMousePosition({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      }
    };

    const heroElement = heroRef.current;
    if (heroElement) {
      heroElement.addEventListener('mousemove', handleMouseMove);
    }

    return () => {
      if (heroElement) {
        heroElement.removeEventListener('mousemove', handleMouseMove);
      }
    };
  }, []);

  return (
    <section ref={heroRef} className="relative min-h-[60vh] flex items-center justify-center overflow-hidden pt-16 pb-8">
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
        {HERO_PARTICLES.map((p) => (
            <div
              key={p.key}
              className="absolute rounded-full transition-all duration-1000 ease-out"
              style={{
                width: `${p.size}px`,
                height: `${p.size}px`,
                left: `${p.baseX}%`,
                top: `${p.baseY}%`,
                background: `radial-gradient(circle, rgba(6, 182, 212, ${p.opacity}) 0%, transparent 70%)`,
                filter: 'blur(1px)',
                transform: `translate(${(mousePosition.x - p.baseX) * 0.02}px, ${(mousePosition.y - p.baseY) * 0.02}px)`,
                transition: 'transform 0.3s ease-out',
                animation: `float ${p.duration}s ease-in-out infinite`,
                animationDelay: `${p.delay}s`,
              }}
            />
          ))}
      </div>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) scale(1); opacity: 0.3; }
          50% { transform: translateY(-20px) scale(1.1); opacity: 0.8; }
        }
      `}</style>

      {/* Gradient Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center">
          {/* Particle Effect Behind Title */}
          <div className="relative mb-8">
            <ParticleEffect />
            {/* Main Heading */}
            <h1 className="relative text-7xl sm:text-8xl md:text-9xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 tracking-tighter animate-in fade-in zoom-in duration-1000 hover:scale-105 transition-transform duration-300"
                style={{
                  filter: 'drop-shadow(0 0 30px rgba(6,182,212,0.5))',
                  textShadow: '0 0 60px rgba(6,182,212,0.3)',
                  position: 'relative',
                  zIndex: 10
                }}>
              TRACENET
            </h1>
          </div>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            NetTrace è lo strumento automatizzato per la tracciatura e l&apos;analisi dei pacchetti di rete.
            Simula, traccia e analizza il comportamento dei pacchetti in reti complesse.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-24">
            <Button
              size="lg"
              className="bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-6 text-lg group"
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              onClick={() => navigate('/generator')}
            >
              Inizia Gratuitamente
              <ArrowRight className={`w-5 h-5 ml-2 transition-transform ${isHovered ? 'translate-x-1' : ''}`} />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg"
              onClick={() => document.getElementById('cisco-section')?.scrollIntoView({ behavior: 'smooth' })}
            >
              Scarica Cisco
            </Button>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mt-32">
          {[
            {
              icon: Zap,
              title: 'Generatore di file .pkt',
              description: 'Genera una rete Cisco con una semplice descrizione.',
            },
            {
              icon: Brain,
              title: 'AI Integrata',
              description: 'Modello di intelligenza artificiale pre-addestrato per creare il tuo file .pkt.',
            },
            {
              icon: Activity,
              title: 'Analisi File .pkt',
              description: 'Carica il tuo file .pkt e analizzalo per capire dove hai sbagliato.',
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

        {/* Vuoi contribuire? Section */}
        <div className="mt-60 text-center">
          <h2 className="text-2xl font-bold text-white mb-8">Vuoi contribuire?</h2>
          <div className="max-w-4xl mx-auto p-12 rounded-2xl bg-slate-900/50 border border-slate-800">
            <p className="text-slate-300 mb-6">
              TraceNet è un progetto open source. Contribuisci con codice, bug report o idee nuove!
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                variant="outline"
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
                onClick={() => window.open('https://github.com/FilippoAutiero007/TraceNet', '_blank')}
              >
                <Github className="w-5 h-5 mr-2" />
                Vai su GitHub
              </Button>
            </div>
          </div>
        </div>

        {/* Non hai Cisco? Section */}
        <div id="cisco-section" className="mt-60 text-center">
          <h2 className="text-2xl font-bold text-white mb-8">Non hai Cisco Packet Tracer?</h2>
          <div className="max-w-4xl mx-auto p-12 rounded-2xl bg-slate-900/50 border border-slate-800">
            <p className="text-slate-300 mb-6">
              Per aprire i file .pkt generati da TraceNet, devi installare Cisco Packet Tracer.
              È disponibile gratuitamente per studenti e docenti.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                variant="outline"
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
                onClick={() => window.open('https://www.netacad.com/resources/lab/cisco-packet-tracer-resources', '_blank')}
              >
                Scarica Cisco Packet Tracer
              </Button>
              <Button
                size="lg"
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
                onClick={() => window.open('https://github.com/FilippoAutiero007/TraceNet/releases/download/1.0/Packet_Tracer822_0400_64bit_setup_signed.exe', '_blank')}
              >
                Download Veloce
              </Button>
            </div>
            <p className="text-slate-500 text-sm mt-4 flex items-center justify-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              TraceNet funziona solo con Cisco Packet Tracer versione 8.x.x
            </p>
          </div>
        </div>

        {/* Non sai come usarlo? */}
        <div className="mt-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-8">Non sai come usarlo?</h2>
          <div className="max-w-4xl mx-auto p-12 rounded-2xl bg-slate-900/50 border border-slate-800">
            <p className="text-slate-300 mb-6">
              Scopri come utilizzare al meglio Cisco Packet Tracer per aprire e gestire i file .pkt generati da TraceNet.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="bg-cyan-500 hover:bg-cyan-600 text-white"
                onClick={() => window.open('https://www.netacad.com/cisco-packet-tracer', '_blank')}
              >
                Impara subito
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
