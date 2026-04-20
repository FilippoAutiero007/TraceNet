import { useState } from 'react';
import { 
  Network, 
  Cpu, 
  BarChart3, 
  FileCode, 
  Code2,
  Terminal
} from 'lucide-react';

const features = [
  {
    id: 'simulation',
    icon: Network,
    title: 'Simulazione di Rete',
    description: 'Crea e simula reti complesse con topologie personalizzabili.',
    details: [
      'Topologie: Mesh, Star, Bus, Ring',
      'Configurazione drag-and-drop',
      'Parametri personalizzabili (delay, bandwidth, packet loss)',
      'Salvataggio progetti multipli',
    ],
  },
  {
    id: 'tracing',
    icon: Cpu,
    title: 'Tracciamento Pacchetti',
    description: 'Traccia ogni pacchetto attraverso la rete in tempo reale.',
    details: [
      'Visualizzazione percorso pacchetti',
      'Timestamp precisi',
      'Analisi header a ogni hop',
      'Highlighting errori e perdite',
    ],
  },
  {
    id: 'analysis',
    icon: BarChart3,
    title: 'Analisi Avanzata',
    description: 'Ottieni insight dettagliati sulle performance della rete.',
    details: [
      'Statistiche in tempo reale',
      'Metriche di latenza e throughput',
      'Grafici e visualizzazioni',
      'Confronto tra simulazioni',
    ],
  },
  {
    id: 'export',
    icon: FileCode,
    title: 'Esportazione Dati',
    description: 'Esporta i risultati in vari formati per analisi esterne.',
    details: [
      'Formato PCAP compatibile Wireshark',
      'JSON per integrazioni API',
      'CSV per analisi in Excel',
      'Report PDF automatici',
    ],
  },
];


export function Features() {
  const [activeFeature, setActiveFeature] = useState('simulation');

  return (
    <section id="features" className="py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Funzionalità Potenti per Professionisti
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Tutto ciò di cui hai bisogno per simulare, tracciare e analizzare reti complesse 
            in un unico strumento intuitivo.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Feature List */}
          <div className="space-y-4">
            {features.map((feature) => (
              <div
                key={feature.id}
                className={`p-6 rounded-xl cursor-pointer transition-all ${
                  activeFeature === feature.id
                    ? 'bg-cyan-500/10 border border-cyan-500/30'
                    : 'bg-slate-900/50 border border-slate-800 hover:border-slate-700'
                }`}
                onClick={() => setActiveFeature(feature.id)}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${
                    activeFeature === feature.id ? 'bg-cyan-500/20' : 'bg-slate-800'
                  }`}>
                    <feature.icon className={`w-6 h-6 ${
                      activeFeature === feature.id ? 'text-cyan-400' : 'text-slate-400'
                    }`} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">{feature.title}</h3>
                    <p className="text-slate-400 text-sm">{feature.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Feature Details */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            {features.map((feature) => (
              activeFeature === feature.id && (
                <div key={feature.id} className="animate-in fade-in duration-300">
                  <div className="flex items-center gap-3 mb-6">
                    <feature.icon className="w-8 h-8 text-cyan-400" />
                    <h3 className="text-2xl font-bold text-white">{feature.title}</h3>
                  </div>
                  <ul className="space-y-3">
                    {feature.details.map((detail, index) => (
                      <li key={index} className="flex items-center gap-3 text-slate-300">
                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                        {detail}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
