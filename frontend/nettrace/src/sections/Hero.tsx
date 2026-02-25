import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowRight, Activity, Shield, Zap, Network } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

export function Hero() {
  const { t } = useLanguage();

  return (
    <section className="relative min-h-screen flex items-center justify-center bg-slate-950 overflow-hidden pt-16">
      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: `linear-gradient(rgba(6,182,212,1) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,1) 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
        aria-hidden="true"
      />
      <div className="absolute top-1/3 left-1/3 w-[500px] h-[500px] bg-cyan-500/8 rounded-full blur-3xl pointer-events-none" aria-hidden="true" />
      <div className="absolute bottom-1/3 right-1/3 w-[400px] h-[400px] bg-purple-600/8 rounded-full blur-3xl pointer-events-none" aria-hidden="true" />

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 mb-7">
          <Activity className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
          <span className="text-cyan-400 text-sm font-medium">{t('hero.badge')}</span>
        </div>

        {/* Heading */}
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold mb-5 tracking-tight">
          <span className="text-white">Net</span>
          <span className="text-cyan-400">Trace</span>
        </h1>

        {/* Tagline */}
        <p className="text-xl sm:text-2xl font-semibold text-white mb-4">{t('hero.tagline')}</p>

        {/* Subtitle */}
        <p className="text-base text-slate-400 max-w-xl mx-auto mb-10 leading-relaxed">
          {t('hero.subtitle')} <strong className="text-slate-300">.pkt</strong> {t('hero.subtitle2')}
        </p>

        {/* CTA */}
        <div className="flex items-center justify-center mb-16">
          <Link to="/generator">
            <Button
              size="lg"
              className="bg-cyan-500 hover:bg-cyan-400 text-white px-8 py-6 text-base font-semibold shadow-xl shadow-cyan-500/25 group focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
            >
              {t('hero.cta')}
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
            </Button>
          </Link>
        </div>

        {/* Feature cards */}
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { icon: Zap, title: t('hero.card1.title'), desc: t('hero.card1.desc') },
            { icon: Shield, title: t('hero.card2.title'), desc: t('hero.card2.desc') },
            { icon: Network, title: t('hero.card3.title'), desc: t('hero.card3.desc') },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 hover:bg-slate-900/80 transition-all text-left"
            >
              <div className="p-2 rounded-lg bg-cyan-500/10 w-fit mb-3">
                <Icon className="w-5 h-5 text-cyan-400" aria-hidden="true" />
              </div>
              <h3 className="text-sm font-semibold text-white mb-1.5">{title}</h3>
              <p className="text-slate-400 text-xs leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
