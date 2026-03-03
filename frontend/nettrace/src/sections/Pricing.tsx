import { Check, Sparkles, Crown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SignUpButton } from '@clerk/clerk-react';
import { motion, type Easing } from 'framer-motion';

const clerkEnabled = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const PRO_FEATURES = [
  'Nodi illimitati',
  'Progetti illimitati',
  'Topologie avanzate (Mesh, Ring)',
  'Export PKT, XML, JSON, CSV',
  'Supporto prioritario',
  'Accesso API completo',
  'Integrazione ChatGPT 4.5',
];

export function Pricing() {
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

  const cardVariants = {
    hidden: { y: 50, opacity: 0, scale: 0.95 },
    visible: {
      y: 0,
      opacity: 1,
      scale: 1,
      transition: { duration: 0.6, ease: "easeOut" as Easing },
    },
  };

  return (
    <section id="pricing" className="py-20 sm:py-24 bg-gradient-to-b from-slate-900 to-slate-950">
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
              <Crown className="w-4 h-4 text-cyan-400" aria-hidden="true" />
              <span className="text-cyan-400 text-sm font-medium">Pricing</span>
            </div>
          </motion.div>
          <motion.h2 variants={itemVariants} className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4 sm:mb-6">
            Simple, Transparent Pricing
          </motion.h2>
          <motion.p variants={itemVariants} className="text-slate-400 max-w-xl mx-auto text-base sm:text-lg leading-relaxed">
            One plan. All features. Free updates included.
          </motion.p>
        </motion.div>

        <motion.div 
          className="flex justify-center"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={containerVariants}
        >
          <motion.div 
            variants={cardVariants}
            className="relative rounded-2xl sm:rounded-3xl p-6 sm:p-8 lg:p-10 bg-gradient-to-br from-slate-900 via-slate-900/95 to-slate-800/90 border-2 border-cyan-500/50 w-full max-w-sm shadow-2xl shadow-cyan-500/20 backdrop-blur-sm"
          >
            <div className="absolute -top-3.5 sm:-top-4 left-1/2 -translate-x-1/2">
              <span className="bg-gradient-to-r from-cyan-500 to-blue-500 text-white text-xs sm:text-sm font-semibold px-4 py-1.5 rounded-full shadow-lg shadow-cyan-500/25">
                Most Popular
              </span>
            </div>

            <motion.div 
              className="mb-6 sm:mb-8"
              variants={itemVariants}
              transition={{ delay: 0.1 }}
            >
              <div className="p-3 sm:p-4 rounded-xl bg-gradient-to-br from-cyan-500/15 to-blue-500/15 w-fit mb-4 sm:mb-6 mx-auto sm:mx-0">
                <Sparkles className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400" aria-hidden="true" />
              </div>
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-2 text-center sm:text-left">Pro</h3>
              <p className="text-slate-400 text-sm sm:text-base text-center sm:text-left">For professionals and teams</p>
            </motion.div>

            <motion.div 
              className="mb-6 sm:mb-8 text-center sm:text-left"
              variants={itemVariants}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-baseline gap-1 justify-center sm:justify-start">
                <span className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white">€14.99</span>
                <span className="text-slate-400 text-sm sm:text-base">/month</span>
              </div>
              <p className="text-slate-500 text-xs sm:text-sm mt-1 sm:mt-2">or €149.99 / year — save 17%</p>
            </motion.div>

            <motion.ul 
              className="space-y-3 sm:space-y-4 mb-8 sm:mb-10"
              variants={itemVariants}
              transition={{ delay: 0.3 }}
            >
              {PRO_FEATURES.map((feature, index) => (
                <motion.li 
                  key={feature} 
                  className="flex items-center gap-3"
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.4 + index * 0.05 }}
                >
                  <div className="w-5 h-5 rounded-full bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-white" aria-hidden="true" />
                  </div>
                  <span className="text-slate-200 text-sm sm:text-base">{feature}</span>
                </motion.li>
              ))}
            </motion.ul>

            <motion.div 
              variants={itemVariants}
              transition={{ delay: 0.5 }}
            >
              {clerkEnabled ? (
                <SignUpButton mode="modal">
                  <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-semibold py-4 sm:py-5 sm:py-6 text-base sm:text-lg shadow-lg shadow-cyan-500/20 focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 transform transition-all duration-300 hover:scale-105">
                    Get Started with Pro
                  </Button>
                </SignUpButton>
              ) : (
                <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold py-4 sm:py-5 sm:py-6 text-base sm:text-lg cursor-not-allowed opacity-75" disabled>
                  Get Started with Pro
                </Button>
              )}
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
