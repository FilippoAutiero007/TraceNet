import { Button } from '@/components/ui/button';
import { ArrowRight, Shield, Zap, Activity, Globe, Database, Cpu, Lock, BarChart3, Code2, Users, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Footer } from '@/sections/Footer';

export function Features() {
  const navigate = useNavigate();
 
  const features = [
    {
      icon: Activity,
      title: 'Generatore di file .pkt',
      description: 'Genera una rete Cisco con una semplice descrizione.',
      details: ['Descrizione in linguaggio naturale', 'File .pkt pronto per Packet Tracer', 'Topologie personalizzabili']
    },
    {
      icon: Shield,
      title: 'Analisi Sicura',
      description: 'Ambiente isolato per testare configurazioni senza rischi per la rete reale.',
      details: ['Sandbox virtuale', 'Test non invasivi', 'Isolamento completo']
    },
    {
      icon: Database,
      title: 'Analisi File .pkt',
      description: 'Carica il tuo file .pkt e analizzalo per capire dove hai sbagliato.',
      details: ['Correzione automatica', 'Suggerimenti dettagliati', 'Report in PDF']
    },
    {
      icon: Zap,
      title: 'Performance Elevate',
      description: 'Analisi di migliaia di pacchetti al secondo con latenza minima.',
      details: ['High-speed processing', 'Low latency', 'Scalabile']
    },
    {
      icon: Globe,
      title: 'Supporto Multi-protocollo',
      description: 'Compatibile con TCP, UDP, HTTP, HTTPS e molti altri protocolli.',
      details: ['Protocolli standard', 'Custom protocols', 'Extensible']
    },
    {
      icon: Cpu,
      title: 'AI-Powered Analysis',
      description: 'Intelligenza artificiale per identificare anomalie e pattern complessi.',
      details: ['Machine learning', 'Pattern recognition', 'Anomaly detection']
    },
    
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
            Funzionalità Avanzate
          </h1>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-12">
            Scopri tutte le potenti funzionalità che rendono TraceNet lo strumento definitivo 
            per l'analisi di rete professionale.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              className="bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-6 text-lg"
              onClick={() => navigate('/pricing')}
            >
              Vedi i Prezzi
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              size="lg"
              className="bg-white hover:bg-gray-100 text-black px-8 py-6 text-lg font-semibold"
              onClick={() => navigate('/generator')}
            >
              Prova Gratis
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/50 transition-all duration-300 group"
              >
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-8 h-8 text-cyan-400" />
                </div>
                
                <h3 className="text-2xl font-bold text-white mb-4">{feature.title}</h3>
                <p className="text-slate-400 mb-6 leading-relaxed">{feature.description}</p>
                
                <ul className="space-y-2">
                  {feature.details.map((detail, detailIndex) => (
                    <li key={detailIndex} className="flex items-center text-sm text-slate-500">
                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full mr-3"></div>
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
