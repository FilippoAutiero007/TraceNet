import { useState } from 'react';
import { Zap, Settings, Download, Sparkles } from 'lucide-react';
import { motion, type Easing } from 'framer-motion';

const features = [
  { 
    id: 'instant', 
    icon: Zap, 
    title: 'Generazione Istantanea', 
    description: 'Scrivi "3 router con OSPF e 2 switch" — il tuo file .pkt è pronto in secondi.',
    details: [
      'Descrizione in linguaggio naturale',
      'Elaborazione in tempo reale',
      'Supporto italiano e inglese',
      'Risultati immediati'
    ] 
  },
  { 
    id: 'automatic', 
    icon: Settings, 
    title: 'Configurazione Automatica', 
    description: 'IP, routing, VLAN e interfacce configurati correttamente in automatico.',
    details: [
      'IP addressing automatico',
      'Protocolli di routing pre-configurati',
      'VLAN e subnetting automatico',
      'Interfacce correttamente parametrizzate'
    ] 
  },
  { 
    id: 'ready', 
    icon: Download, 
    title: 'Pronto per Cisco PT', 
    description: 'File .pkt compatibile — aprilo direttamente in Cisco Packet Tracer.',
    details: [
      'Compatibilità 100% Cisco Packet Tracer',
      'File pronto all\'uso',
      'Nessuna configurazione manuale',
      'Apri e inizia a simulare'
    ] 
  },
];

export function Features() {
  const [activeFeature, setActiveFeature] = useState('instant');

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
    hidden: { y: 30, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5, ease: "easeOut" as Easing },
    },
  };

  return (
    <section id="features" className="py-20 sm:py-24 bg-gradient-to-b from-slate-950 to-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div 
          className="text-center mb-12 sm:mb-16"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={containerVariants}
        >
          <motion.div variants={itemVariants} className="mb-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/25">
              <Sparkles className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              <span className="text-cyan-400 text-sm font-medium">Features</span>
            </div>
          </motion.div>
          <motion.h2 variants={itemVariants} className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 sm:mb-6">
            Tutto ciò che ti serve
          </motion.h2>
          <motion.p variants={itemVariants} className="text-slate-400 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            Generazione automatica, configurazione intelligente e compatibilità totale con Cisco Packet Tracer.
          </motion.p>
        </motion.div>

        <motion.div 
          className="grid lg:grid-cols-2 gap-8 lg:gap-12 items-start"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={containerVariants}
        >
          <div className="space-y-3 sm:space-y-4">
            {features.map((feature, index) => (
              <motion.button
                key={feature.id}
                variants={itemVariants}
                transition={{ delay: index * 0.1 }}
                className={`w-full p-4 sm:p-5 rounded-xl text-left transition-all focus-visible:ring-2 focus-visible:ring-cyan-500 ${
                  activeFeature === feature.id 
                    ? 'bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 shadow-lg shadow-cyan-500/10' 
                    : 'bg-slate-900/50 border border-slate-800 hover:border-slate-600 hover:bg-slate-900/70'
                }`}
                onClick={() => setActiveFeature(feature.id)}
                aria-pressed={activeFeature === feature.id}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 sm:p-3 rounded-lg transition-all ${
                    activeFeature === feature.id 
                      ? 'bg-gradient-to-br from-cyan-500/20 to-blue-500/20' 
                      : 'bg-slate-800'
                  }`}>
                    <feature.icon className={`w-5 h-5 sm:w-6 sm:h-6 transition-colors ${
                      activeFeature === feature.id ? 'text-cyan-400' : 'text-slate-400'
                    }`} aria-hidden="true" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base sm:text-lg font-semibold text-white mb-1 sm:mb-2">{feature.title}</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>

          <motion.div 
            className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 border border-slate-700/50 rounded-2xl p-6 sm:p-8 shadow-xl"
            variants={itemVariants}
            transition={{ delay: 0.3 }}
          >
            {features.map((feature) => activeFeature === feature.id && (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                    <feature.icon className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" aria-hidden="true" />
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white">{feature.title}</h3>
                </div>
                <ul className="space-y-3 sm:space-y-4">
                  {feature.details.map((detail, index) => (
                    <motion.li 
                      key={detail} 
                      className="flex items-center gap-3 text-slate-300 text-sm sm:text-base"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <div className="w-2 h-2 rounded-full bg-gradient-to-r from-cyan-400 to-blue-400 flex-shrink-0" aria-hidden="true" />
                      {detail}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
