import { useState } from 'react';
import { Check, X, Sparkles, GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { SignUpButton } from '@clerk/clerk-react';

const plans = [
  {
    id: 'free',
    name: 'Free',
    description: 'Per studenti e hobbisti',
    price: { monthly: 0, yearly: 0 },
    icon: GraduationCap,
    features: [
      { text: '5 nodi per simulazione', included: true },
      { text: '5 progetti salvati', included: true },
      { text: 'Topologie base', included: true },
      { text: 'Supporto community', included: true },
      { text: 'Generazione file .pkt limitata (10 al mese)', included: true },
      { text: 'Pubblicità dopo ogni generazione', included: true },
      { text: 'Esportazione JSON', included: false },
      { text: 'Analisi avanzata', included: false },
      { text: 'API access', included: false },
    ],
    cta: 'Inizia Gratis',
    popular: false,
  },
  {
    id: 'professional',
    name: 'Professional',
    description: 'Per professionisti e team',
    price: { monthly: 4.99, yearly: 30 },
    icon: Sparkles,
    features: [
      { text: 'Nodi illimitati', included: true },
      { text: 'Progetti illimitati', included: true },
      { text: 'Tutte le topologie', included: true },
      { text: 'Supporto prioritario', included: true },
      { text: 'Esportazione PCAP, JSON, CSV', included: true },
      { text: 'Analisi avanzata AI', included: true },
      { text: 'API access completo', included: true },
      { text: 'Generazione infinita file .pkt', included: true },
      { text: '0 pubblicità', included: true },
      { text: 'Controllo inverso (carica file .pkt per trovare errori)', included: true, comingSoon: true },
      { text: 'Modello Mistral AI', included: true },
    ],
    cta: 'Scegli Professional',
    popular: true,
  },
];

export function Pricing() {
  const [isYearly, setIsYearly] = useState(false);

  return (
    <section id="pricing" className="py-24 bg-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Scegli il Piano Perfetto per Te
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto mb-8">
            Inizia gratuitamente e scala quando ne hai bisogno. 
            Tutti i piani includono aggiornamenti gratuiti.
          </p>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4">
            <span className={`text-sm ${!isYearly ? 'text-white' : 'text-slate-500'}`}>
              Mensile
            </span>
            <Switch
              checked={isYearly}
              onCheckedChange={setIsYearly}
            />
            <span className={`text-sm ${isYearly ? 'text-white' : 'text-slate-500'}`}>
              Annuale
            </span>
            {isYearly && (
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
                Risparmia 20%
              </span>
            )}
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl p-6 ${
                plan.popular
                  ? 'bg-gradient-to-b from-cyan-500/20 to-slate-900 border-2 border-cyan-500'
                  : 'bg-slate-950 border border-slate-800'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-cyan-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Più Popolare
                  </span>
                </div>
              )}

              
              <div className="mb-6">
                <plan.icon className={`w-10 h-10 mb-4 ${
                  plan.popular ? 'text-cyan-400' : 'text-slate-400'
                }`} />
                <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
                <p className="text-slate-500 text-sm">{plan.description}</p>
              </div>

              <div className="mb-6">
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-white">
                    €{isYearly ? plan.price.yearly : plan.price.monthly}
                  </span>
                  <span className="text-slate-500 text-sm">
                    /{isYearly ? 'anno' : 'mese'}
                  </span>
                </div>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-3">
                    {feature.included ? (
                      <Check className="w-5 h-5 text-green-400 flex-shrink-0" />
                    ) : (
                      <X className="w-5 h-5 text-slate-600 flex-shrink-0" />
                    )}
                    <span className={`text-sm ${
                      feature.included ? 'text-slate-300' : 'text-slate-600'
                    }`}>
                      {feature.text}
                      {feature.comingSoon && (
                        <span className="text-xs text-cyan-400 ml-2">(Presto in arrivo)</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>

              <SignUpButton mode="modal">
                <Button
                  className={`w-full ${
                    plan.popular
                      ? 'bg-cyan-500 hover:bg-cyan-600 text-white'
                      : 'bg-slate-800 hover:bg-slate-700 text-white'
                  }`}
                >
                  {plan.cta}
                </Button>
              </SignUpButton>
            </div>
          ))}
        </div>

        {/* FAQ Note */}
        <div className="mt-12 text-center">
          <p className="text-slate-500 text-sm">
            Hai domande? Consulta la nostra{' '}
            <a href="#" className="text-cyan-400 hover:underline">
              documentazione
            </a>{' '}
            o{' '}
            <a href="#" className="text-cyan-400 hover:underline">
              contattaci
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
