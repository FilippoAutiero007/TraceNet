import { useState } from 'react';
import { Link } from 'react-router-dom';
import { SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/clerk-react';
import { Button } from '@/components/ui/button';
import { Network, Menu, X } from 'lucide-react';

export function Navigation() {
  const { isSignedIn } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: '/features', label: 'Funzionalità' },
    { href: '/generator', label: 'Generatore' },
    { href: '/analisi', label: 'Analisi' },
    { href: '/pricing', label: 'Prezzi' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <Network className="w-8 h-8 text-cyan-400" />
            <span className="text-xl font-bold text-white">TraceNet</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className="text-slate-300 hover:text-cyan-400 transition-colors text-sm font-medium"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Auth Buttons */}
          <div className="hidden md:flex items-center gap-4">
            {isSignedIn ? (
              <UserButton afterSignOutUrl="/" />
            ) : (
              <>
                <SignInButton mode="modal">
                  <Button variant="ghost" className="text-slate-300 hover:text-white">
                    Accedi
                  </Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button variant="outline" className="border-cyan-500 text-black hover:bg-cyan-500 hover:text-white">
                    Registrati
                  </Button>
                </SignUpButton>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-slate-300"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-800">
            <div className="flex flex-col gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  className="text-slate-300 hover:text-cyan-400 transition-colors px-2 py-1"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              <div className="flex flex-col gap-2 pt-4 border-t border-slate-800">
                {isSignedIn ? (
                  <div className="px-2">
                    <UserButton afterSignOutUrl="/" />
                  </div>
                ) : (
                  <>
                    <SignInButton mode="modal">
                      <Button variant="ghost" className="w-full justify-start text-slate-300">
                        Accedi
                      </Button>
                    </SignInButton>
                    <SignUpButton mode="modal">
                      <Button variant="outline" className="w-full border-cyan-500 text-cyan-500">
                        Registrati
                      </Button>
                    </SignUpButton>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
