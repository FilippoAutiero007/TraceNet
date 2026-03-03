import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowRight, Shield, Zap, Network, Sparkles } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { motion, type Easing } from 'framer-motion';

export function Hero() {
  const { t } = useLanguage();

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
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5, ease: "easeOut" as Easing },
    },
  };

  const cardVariants = {
    hidden: { y: 30, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.6, ease: "easeOut" as Easing },
    },
  };

  return (
    <section className="relative min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 overflow-hidden pt-16">
      {/* Enhanced background */}
      <div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: `linear-gradient(rgba(6,182,212,1) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,1) 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
        aria-hidden="true"
      />
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none animate-pulse" aria-hidden="true" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-purple-600/8 rounded-full blur-3xl pointer-events-none animate-pulse" aria-hidden="true" />
      <div className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-blue-600/6 rounded-full blur-3xl pointer-events-none animate-pulse" aria-hidden="true" />

      <motion.div 
        className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Badge */}
        <motion.div variants={itemVariants} className="mb-6 sm:mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/25 backdrop-blur-sm">
            <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" aria-hidden="true" />
            <span className="text-cyan-400 text-sm font-medium">{t('hero.badge')}</span>
          </div>
        </motion.div>

        {/* Heading */}
        <motion.h1 
          variants={itemVariants}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-extrabold mb-6 sm:mb-8 tracking-tight leading-tight"
        >
          <span className="bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">Net</span>
          <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">Trace</span>
        </motion.h1>

        {/* Tagline */}
        <motion.p 
          variants={itemVariants}
          className="text-xl sm:text-2xl md:text-3xl font-semibold text-white mb-4 sm:mb-6 leading-tight"
        >
          {t('hero.tagline')}
        </motion.p>

        {/* Subtitle */}
        <motion.p 
          variants={itemVariants}
          className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto mb-10 sm:mb-12 leading-relaxed"
        >
          {t('hero.subtitle')} <strong className="text-slate-300 font-semibold">.pkt</strong> {t('hero.subtitle2')}
        </motion.p>

        {/* CTA */}
        <motion.div variants={itemVariants} className="flex items-center justify-center mb-16 sm:mb-20">
          <Link to="/generator">
            <Button
              size="lg"
              className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white px-8 py-6 text-base sm:text-lg font-semibold shadow-xl shadow-cyan-500/25 group focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 transform transition-all duration-300 hover:scale-105"
            >
              {t('hero.cta')}
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform duration-300" aria-hidden="true" />
            </Button>
          </Link>
        </motion.div>

        {/* Feature cards */}
        <motion.div 
          variants={containerVariants}
          className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-4xl mx-auto"
        >
          {[
            { icon: Zap, title: t('hero.card1.title'), desc: t('hero.card1.desc'), delay: 0.2 },
            { icon: Shield, title: t('hero.card2.title'), desc: t('hero.card2.desc'), delay: 0.3 },
            { icon: Network, title: t('hero.card3.title'), desc: t('hero.card3.desc'), delay: 0.4 },
          ].map(({ icon: Icon, title, desc, delay }) => (
            <motion.div
              key={title}
              variants={cardVariants}
              transition={{ delay }}
              className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-slate-900/60 to-slate-800/40 border border-slate-700/50 hover:border-cyan-500/40 hover:bg-gradient-to-br hover:from-slate-900/80 hover:to-slate-800/60 transition-all duration-300 text-left group hover:shadow-lg hover:shadow-cyan-500/10"
            >
              <div className="p-3 rounded-lg bg-gradient-to-br from-cyan-500/10 to-blue-500/10 w-fit mb-4 group-hover:from-cyan-500/20 group-hover:to-blue-500/20 transition-all duration-300">
                <Icon className="w-5 h-5 text-cyan-400" aria-hidden="true" />
              </div>
              <h3 className="text-sm sm:text-base font-semibold text-white mb-2">{title}</h3>
              <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">{desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </section>
  );
}
