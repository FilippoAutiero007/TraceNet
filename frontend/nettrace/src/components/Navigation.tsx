import { useState } from 'react';
import { Link } from 'react-router-dom';
import { SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/clerk-react';
import { Button } from '@/components/ui/button';
import { Network, Menu, X, Zap, LogIn, Globe } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

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
  const { t, lang, toggle } = useLanguage();

  const navLinks = [
    { href: '#features', label: t('nav.features') },
    { href: '#pricing', label: t('nav.pricing') },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/95 backdrop-blur-md border-b border-slate-800/60" role="navigation" aria-label="Main navigation">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group focus-visible:ring-2 focus-visible:ring-cyan-500 rounded" aria-label="NetTrace — home">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 group-hover:bg-cyan-500/20 transition-colors">
              <Network className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            </div>
            <span className="text-base font-bold text-white tracking-tight">Net<span className="text-cyan-400">Trace</span></span>
          </Link>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-slate-300 hover:text-white transition-colors text-sm font-medium focus-visible:ring-2 focus-visible:ring-cyan-500 rounded"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop actions */}
          <div className="hidden md:flex items-center gap-2">
            {/* Language toggle */}
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

            <Link to="/generator">
              <Button
                size="sm"
                className="bg-cyan-500 hover:bg-cyan-400 text-white font-semibold shadow-md shadow-cyan-500/20 focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
                aria-label={t('nav.generator')}
              >
                <Zap className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                {t('nav.generator')}
              </Button>
            </Link>

            {clerkEnabled ? (
              <ClerkAuthDesktop />
            ) : (
              <Button size="sm" variant="outline" className="border-slate-200 bg-white text-slate-900/60 cursor-not-allowed" disabled aria-label={t('nav.signin')}>
                <LogIn className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                {t('nav.signin')}
              </Button>
            )}
          </div>

          {/* Mobile toggle */}
          <div className="md:hidden flex items-center gap-2">
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
            <button
              className="text-slate-300 hover:text-white p-2 rounded focus-visible:ring-2 focus-visible:ring-cyan-500"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-expanded={mobileOpen}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            >
              {mobileOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden py-4 border-t border-slate-800">
            <div className="flex flex-col gap-2">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-slate-200 hover:text-white px-2 py-2 rounded hover:bg-slate-800 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-cyan-500"
                  onClick={() => setMobileOpen(false)}
                >
                  {link.label}
                </a>
              ))}
              <div className="flex flex-col gap-2 pt-3 border-t border-slate-800">
                <Link to="/generator" onClick={() => setMobileOpen(false)}>
                  <Button className="w-full bg-cyan-500 hover:bg-cyan-400 text-white font-semibold">
                    <Zap className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t('nav.generator')}
                  </Button>
                </Link>
                {clerkEnabled ? (
                  <ClerkAuthMobile onClose={() => setMobileOpen(false)} />
                ) : (
                  <Button variant="outline" className="w-full border-slate-200 bg-white text-slate-900/50" disabled>{t('nav.signin')}</Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
