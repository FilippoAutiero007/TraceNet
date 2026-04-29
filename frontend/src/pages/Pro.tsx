import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Crown, Zap, Shield, Users, Database, BarChart3, Code2, Settings, Star } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Pro() {
  const navigate = useNavigate();
  const [selectedPlan, setSelectedPlan] = useState('monthly');

  const proFeatures = [
    { icon: Database, title: '100.000+ Pacchetti', description: 'Analisi fino a 100.000 pacchetti per sessione' },
    { icon: Zap, title: 'Simulazioni Avanzate', description: 'Simulazioni complesse con algoritmi AI' },
    { icon: Shield, title: 'Sicurezza Enterprise', description: 'Crittografia e conformità GDPR' },
    { icon: Users, title: 'Team Collaboration', description: 'Lavora con team fino a 5 utenti' },
    { icon: BarChart3, title: 'Analytics Dashboard', description: 'Dashboard avanzate con metriche dettagliate' },
    { icon: Code2, title: 'API Completa', description: 'API RESTful con webhook e SDK' },
    { icon: Settings, title: 'Automazione', description: 'Script personalizzati e automazione' },
    { icon: Star, title: 'Supporto Prioritario', description: 'Supporto dedicato 24/7' }
  ];

  const testimonials = [
    {
      name: 'Marco Rossi',
      role: 'Network Engineer',
      company: 'TechCorp',
      content: "TraceNet Pro ha rivoluzionato il nostro workflow di analisi di rete. L'API è fantastica!",
      rating: 5
    },
    {
      name: 'Laura Bianchi',
      role: 'Security Analyst',
      company: 'SecureNet',
      content: 'Le funzionalità di team collaboration sono incredibili. Ora lavoriamo in modo più efficiente.',
      rating: 5
    },
    {
      name: 'Giuseppe Verdi',
      role: 'CTO',
      company: 'StartupLab',
      content: 'Il miglior investimento per la nostra infrastruttura di rete. Vale ogni centesimo.',
      rating: 5
    }
  ];

  return (
    <div className="min-h-screen bg-black">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-gradient-to-r from-cyan-500 to-purple-500 text-white border-none">
              Livello Pro
            </Badge>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
              TraceNet Pro
            </h1>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-8">
              Potenza illimitata per professionisti e team che richiedono il massimo dall&apos;analisi di rete.
            </p>
          </div>

          {/* Pricing Toggle */}
          <div className="flex justify-center mb-12">
            <div className="inline-flex items-center rounded-lg bg-slate-800 p-1">
              <button
                className={`px-6 py-2 rounded-md transition-colors ${
                  selectedPlan === 'monthly'
                    ? 'bg-cyan-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                onClick={() => setSelectedPlan('monthly')}
              >
                Mensile
              </button>
              <button
                className={`px-6 py-2 rounded-md transition-colors ${
                  selectedPlan === 'annual'
                    ? 'bg-cyan-500 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
                onClick={() => setSelectedPlan('annual')}
              >
                Annuale (Risparmia 20%)
              </button>
            </div>
          </div>

          {/* Pro Plan Card */}
          <Card className="bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border-cyan-500/30 max-w-2xl mx-auto">
            <CardHeader className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <Crown className="w-10 h-10 text-white" />
              </div>
              <CardTitle className="text-3xl text-white">Piano Pro</CardTitle>
              <CardDescription className="text-slate-300 text-lg">
                Tutto ciò di cui hai bisogno per l&apos;analisi di rete professionale
              </CardDescription>
              <div className="flex items-baseline justify-center gap-2 mt-4">
                <span className="text-6xl font-bold text-white">
                  {selectedPlan === 'monthly' ? '€29' : '€23'}
                </span>
                <span className="text-xl text-slate-400">/mese</span>
              </div>
              {selectedPlan === 'annual' && (
                <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                  Risparmi €72 all&apos;anno
                </Badge>
              )}
            </CardHeader>
            <CardContent className="space-y-6">
              <Button
                size="lg"
                className="w-full bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white py-6 text-lg"
              >
                Inizia Pro Trial di 14 giorni
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>

              <div className="text-center text-slate-400 text-sm">
                Nessuna carta di credito richiesta per il trial
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Pro Features Grid */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Funzionalità Esclusive Pro
          </h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {proFeatures.map((feature, index) => (
              <Card key={index} className="bg-slate-900/50 border-slate-800 hover:border-cyan-500/50 transition-all duration-300 group">
                <CardContent className="p-6 text-center">
                  <div className="w-16 h-16 bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                    <feature.icon className="w-8 h-8 text-cyan-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Free vs Pro
          </h2>

          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-0">
              <div className="grid md:grid-cols-3">
                <div className="p-6 border-r border-slate-800">
                  <h3 className="text-xl font-bold text-white mb-4">Funzionalità</h3>
                </div>
                <div className="p-6 border-r border-slate-800 text-center">
                  <h3 className="text-xl font-bold text-cyan-400 mb-4">Free</h3>
                </div>
                <div className="p-6 text-center">
                  <h3 className="text-xl font-bold text-purple-400 mb-4">Pro</h3>
                </div>
              </div>

              {[
                { feature: 'Pacchetti per sessione', free: '1.000', pro: '100.000+' },
                { feature: 'Team members', free: '1', pro: '5' },
                { feature: 'Export formats', free: 'CSV', pro: 'PCAP, JSON, CSV' },
                { feature: 'API access', free: '✗', pro: '✓' },
                { feature: 'Analytics dashboard', free: '✗', pro: '✓' },
                { feature: 'Priority support', free: '✗', pro: '✓' },
                { feature: 'Custom rules', free: '✗', pro: '✓' },
                { feature: 'Automation', free: '✗', pro: '✓' }
              ].map((item, index) => (
                <div key={index} className="grid md:grid-cols-3 border-t border-slate-800">
                  <div className="p-6 border-r border-slate-800">
                    <p className="text-slate-300">{item.feature}</p>
                  </div>
                  <div className="p-6 border-r border-slate-800 text-center">
                    <p className={`font-semibold ${item.free === '✗' ? 'text-slate-600' : 'text-cyan-400'}`}>
                      {item.free}
                    </p>
                  </div>
                  <div className="p-6 text-center">
                    <p className={`font-semibold ${item.pro === '✗' ? 'text-slate-600' : 'text-purple-400'}`}>
                      {item.pro}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Cosa Dicono i Nostri Clienti Pro
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="bg-slate-900/50 border-slate-800 hover:border-cyan-500/50 transition-colors">
                <CardContent className="p-6">
                  <div className="flex mb-4">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                    ))}
                  </div>
                  <p className="text-slate-300 mb-6 italic">&quot;{testimonial.content}&quot;</p>
                  <div>
                    <p className="text-white font-semibold">{testimonial.name}</p>
                    <p className="text-slate-500 text-sm">{testimonial.role} @ {testimonial.company}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-12 rounded-3xl bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/20">
            <h2 className="text-4xl font-bold text-white mb-6">
              Pronto a Passare al Livello Successivo?
            </h2>
            <p className="text-xl text-slate-300 mb-8">
              Unisciti a migliaia di professionisti che hanno già scelto TraceNet Pro.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 text-white px-8 py-6 text-lg"
              >
                Inizia Pro Trial
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-slate-700 text-slate-300 hover:bg-slate-800 px-8 py-6 text-lg"
                onClick={() => navigate('/free')}
              >
                Confronta con Free
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
