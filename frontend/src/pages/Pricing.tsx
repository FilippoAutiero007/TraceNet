import { Button } from '@/components/ui/button';
import { ArrowRight, Check, Star, Zap, Shield, Crown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Pricing() {
  const navigate = useNavigate();

  const plans = [
    {
      name: 'Free',
      price: '€0',
      period: '/mese',
      description: 'Perfetto per iniziare e progetti personali',
      icon: Star,
      features: [
        'Analisi fino a 1.000 pacchetti',
        'Simulazioni base',
        'Export in formato CSV',
        'Supporto community',
        '1 progetto attivo'
      ],
      excluded: [
        'API access',
        'Team collaboration',
        'Advanced analytics',
        'Priority support'
      ],
      buttonText: 'Inizia Gratis',
      buttonAction: () => navigate('/free'),
      popular: false
    },
    {
      name: 'Pro',
      price: '€29',
      period: '/mese',
      description: 'Per professionisti e team in crescita',
      icon: Zap,
      features: [
        'Analisi fino a 100.000 pacchetti',
        'Simulazioni avanzate',
        'Export multi-formato (PCAP, JSON, CSV)',
        'API RESTful completa',
        'Team collaboration (5 utenti)',
        'Analytics dashboard',
        'Supporto prioritario',
        '10 progetti attivi'
      ],
      excluded: [],
      buttonText: 'Inizia Pro Trial',
      buttonAction: () => navigate('/pro'),
      popular: true
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'Per aziende con esigenze specifiche',
      icon: Crown,
      features: [
        'Pacchetti illimitati',
        'Simulazioni custom',
        'On-premise deployment',
        'SLA garantito',
        'Team illimitato',
        'Integrazioni personalizzate',
        'Dedicated account manager',
        'Training on-site',
        'Progetti illimitati'
      ],
      excluded: [],
      buttonText: 'Contatta Sales',
      buttonAction: () => navigate('/pro'),
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-black">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
            Piani Tariffari
          </h1>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-12">
            Scegli il piano perfetto per le tue esigenze. Dal free trial alle soluzioni enterprise.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              variant="outline"
              className="border-slate-700 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg"
              onClick={() => navigate('/features')}
            >
              Confronta Funzionalità
            </Button>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {plans.map((plan, index) => (
              <div
                key={index}
                className={`relative p-8 rounded-3xl border transition-all duration-300 ${
                  plan.popular
                    ? 'bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border-cyan-500/30 scale-105 shadow-2xl shadow-cyan-500/20'
                    : 'bg-slate-900/50 border-slate-800 hover:border-cyan-500/50'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="px-4 py-1 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full">
                      <span className="text-white text-sm font-semibold">Più Popolare</span>
                    </div>
                  </div>
                )}

                <div className="text-center mb-8">
                  <div className="w-16 h-16 bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <plan.icon className="w-8 h-8 text-cyan-400" />
                  </div>
                  
                  <h3 className="text-3xl font-bold text-white mb-2">{plan.name}</h3>
                  <div className="flex items-baseline justify-center gap-1 mb-4">
                    <span className="text-5xl font-bold text-white">{plan.price}</span>
                    <span className="text-xl text-slate-400">{plan.period}</span>
                  </div>
                  <p className="text-slate-400">{plan.description}</p>
                </div>

                <div className="space-y-4 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-start gap-3">
                      <Check className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
                      <span className="text-slate-300 text-sm">{feature}</span>
                    </div>
                  ))}
                  {plan.excluded.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-start gap-3 opacity-50">
                      <div className="w-5 h-5 border border-slate-600 rounded mt-0.5 flex-shrink-0" />
                      <span className="text-slate-500 text-sm line-through">{feature}</span>
                    </div>
                  ))}
                </div>

                <Button
                  size="lg"
                  className={`w-full py-6 text-lg ${
                    plan.popular
                      ? 'bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white'
                      : 'bg-slate-800 hover:bg-slate-700 text-white border border-slate-700'
                  }`}
                  onClick={plan.buttonAction}
                >
                  {plan.buttonText}
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">Domande Frequenti</h2>
          
          <div className="space-y-6">
            {[
              {
                question: 'Posso cambiare piano in qualsiasi momento?',
                answer: 'Sì, puoi upgrade o downgrade il tuo piano in qualsiasi momento. I cambiamenti diventano effettivi dal prossimo ciclo di fatturazione.'
              },
              {
                question: 'Cosa succede dopo il periodo di prova?',
                answer: 'Al termine del periodo di prova di 14 giorni, puoi scegliere di sottoscrivere un piano a pagamento o continuare con il piano Free.'
              },
              {
                question: 'È disponibile una versione on-premise?',
                answer: 'Sì, il piano Enterprise include opzioni di deployment on-premise con supporto dedicato.'
              },
              {
                question: 'Come funziona la fatturazione?',
                answer: 'La fatturazione è mensile o annuale. Con l\'abbonamento annuale risparmi il 20% rispetto al piano mensile.'
              }
            ].map((faq, index) => (
              <div key={index} className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
                <h3 className="text-xl font-semibold text-white mb-3">{faq.question}</h3>
                <p className="text-slate-400">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-12 rounded-3xl bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/20">
            <h2 className="text-4xl font-bold text-white mb-6">
              Ancora in dubbio?
            </h2>
            <p className="text-xl text-slate-300 mb-8">
              Inizia con il piano gratuito e aggiorna quando sei pronto.
            </p>
            <Button
              size="lg"
              className="bg-cyan-500 hover:bg-cyan-600 text-white px-8 py-6 text-lg"
              onClick={() => navigate('/free')}
            >
              Inizia Gratis Ora
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
