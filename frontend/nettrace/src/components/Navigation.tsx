import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/clerk-react';
import { Button } from '@/components/ui/button';
import { Network, Menu, X, Zap, LogIn, Globe } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { motion, AnimatePresence } from 'framer-motion';

const clerkEnabled = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function ClerkAuthDesktop() {
  const { t } = useLanguage();
  const { isSignedIn } = useAuth();
  if (isSignedIn) return <UserButton afterSignOutUrl="/" />;
  return (
    <>
      <SignInButton mode="modal">
        <Button
          variant="outline"
          size="sm"
          className="border-slate-200 bg-white text-slate-900 hover:bg-slate-100 hover:text-slate-900 gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-500"
          aria-label={t('nav.signin')}
        >
          <LogIn className="h-3.5 w-3.5" aria-hidden="true" />
          {t('nav.signin')}
        </Button>
      </SignInButton>
      <SignUpButton mode="modal">
        <Button
          size="sm"
          className="bg-cyan-500 hover:bg-cyan-400 text-white focus-visible:ring-2 focus-visible:ring-cyan-500"
          aria-label={t('nav.signup')}
        >
          {t('nav.signup')}
        </Button>
      </SignUpButton>
    </>
  );
}

function ClerkAuthMobile({ onClose }: { onClose: () => void }) {
  const { t } = useLanguage();
  const { isSignedIn } = useAuth();
  if (isSignedIn) return <div className="px-1"><UserButton afterSignOutUrl="/" /></div>;
  return (
    <>
      <SignInButton mode="modal">
        <Button
          variant="outline"
          className="w-full border-slate-200 bg-white text-slate-900 hover:bg-slate-100 gap-2 focus-visible:ring-2 focus-visible:ring-cyan-500"
          onClick={onClose}
          aria-label={t('nav.signin')}
        >
          <LogIn className="h-4 w-4" aria-hidden="true" />
          {t('nav.signin')}
        </Button>
      </SignInButton>
      <SignUpButton mode="modal">
        <Button
          className="w-full bg-cyan-500 hover:bg-cyan-400 text-white focus-visible:ring-2 focus-visible:ring-cyan-300"
          onClick={onClose}
          aria-label={t('nav.signup')}
        >
          {t('nav.signup')}
        </Button>
      </SignUpButton>
    </>
  );
}

export function Navigation() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { t, lang, toggle } = useLanguage();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { href: '#features', label: t('nav.features') },
    { href: '#pricing', label: t('nav.pricing') },
    { href: '#contact', label: t('nav.contacts') },
  ];

  const mobileMenuVariants = {
    hidden: { 
      opacity: 0, 
      y: -20,
      transition: { duration: 0.2 }
    },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.3, staggerChildren: 0.1 }
    },
    exit: { 
      opacity: 0, 
      y: -20,
      transition: { duration: 0.2 }
    }
  };

  const mobileItemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0 }
  };

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled 
        ? 'bg-slate-950/95 backdrop-blur-md border-b border-slate-800/60 shadow-lg shadow-slate-900/20' 
        : 'bg-slate-950/80 backdrop-blur-sm border-b border-slate-800/30'
    }`} role="navigation" aria-label="Main navigation">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group focus-visible:ring-2 focus-visible:ring-cyan-500 rounded" aria-label="NetTrace — home">
            <motion.div 
              className="p-1.5 rounded-lg bg-cyan-500/10 group-hover:bg-cyan-500/20 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Network className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            </motion.div>
            <span className="text-base font-bold text-white tracking-tight">Net<span className="text-cyan-400">Trace</span></span>
          </Link>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-4">
            {navLinks.map((link, index) => (
              <motion.a
                key={link.href}
                href={link.href}
                className="text-slate-300 hover:text-white transition-colors text-sm font-medium focus-visible:ring-2 focus-visible:ring-cyan-500 rounded"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                {link.label}
              </motion.a>
            ))}
          </div>

          {/* Desktop actions */}
          <div className="hidden md:flex items-center gap-2">
            {/* Language toggle */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Button
                variant="ghost"
                size="sm"
                onClick={toggle}
                className="text-slate-400 hover:text-white gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-500 px-2"
                aria-label={t('lang.label')}
                title={t('lang.label')}
              >
                <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="text-xs font-semibold">{t('lang.toggle')}</span>
              </Button>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Link to="/generator">
                <Button
                  size="sm"
                  className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-semibold shadow-md shadow-cyan-500/20 focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
                  aria-label={t('nav.generator')}
                >
                  <Zap className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  {t('nav.generator')}
                </Button>
              </Link>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {clerkEnabled ? (
                <ClerkAuthDesktop />
              ) : (
                <Button size="sm" variant="outline" className="border-slate-200 bg-white text-slate-900/60 cursor-not-allowed" disabled aria-label={t('nav.signin')}>
                  <LogIn className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  {t('nav.signin')}
                </Button>
              )}
            </motion.div>
          </div>

          {/* Mobile toggle */}
          <div className="md:hidden flex items-center gap-2">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggle}
                className="text-slate-400 hover:text-white px-2"
                aria-label={t('lang.label')}
              >
                <Globe className="w-4 h-4" aria-hidden="true" />
                <span className="text-xs ml-1 font-semibold">{lang.toUpperCase()}</span>
              </Button>
            </motion.div>
            <motion.button
              className="text-slate-300 hover:text-white p-2 rounded focus-visible:ring-2 focus-visible:ring-cyan-500"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-expanded={mobileOpen}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <AnimatePresence mode="wait">
                {mobileOpen ? (
                  <motion.div key="close" className="w-5 h-5 flex items-center justify-center">
                    <X className="w-5 h-5" />
                  </motion.div>
                ) : (
                  <motion.div key="menu" className="w-5 h-5 flex items-center justify-center">
                    <Menu className="w-5 h-5" />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </div>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div 
              className="md:hidden py-4 border-t border-slate-800"
              variants={mobileMenuVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <div className="flex flex-col gap-2">
                {navLinks.map((link, index) => (
                  <motion.a
                    key={link.href}
                    href={link.href}
                    className="text-slate-200 hover:text-white px-2 py-3 rounded hover:bg-slate-800 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500"
                    onClick={() => setMobileOpen(false)}
                    variants={mobileItemVariants}
                    transition={{ delay: index * 0.05 }}
                  >
                    {link.label}
                  </motion.a>
                ))}
                <motion.div 
                  className="flex flex-col gap-2 pt-3 border-t border-slate-800"
                  variants={mobileItemVariants}
                  transition={{ delay: 0.2 }}
                >
                  <Link to="/generator" onClick={() => setMobileOpen(false)}>
                    <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-semibold">
                      <Zap className="mr-2 h-4 w-4" aria-hidden="true" />
                      {t('nav.generator')}
                    </Button>
                  </Link>
                  {clerkEnabled ? (
                    <ClerkAuthMobile onClose={() => setMobileOpen(false)} />
                  ) : (
                    <Button variant="outline" className="w-full border-slate-200 bg-white text-slate-900/50" disabled>{t('nav.signin')}</Button>
                  )}
                </motion.div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
}
