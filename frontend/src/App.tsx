import { HashRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { Navigation } from '@/components/Navigation';
import { Landing } from '@/pages/Landing';
import { Generator } from '@/pages/Generator';
import { Intro } from '@/pages/Intro';
import { Features } from '@/pages/Features';
import { Pricing } from '@/pages/Pricing';
import { Analisi } from '@/pages/Analisi';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ParticleEffect } from '@/components/ParticleEffect';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <HelmetProvider>
        <HashRouter>
          <div className="relative">
            <div className="fixed inset-0 z-0">
              <ParticleEffect />
            </div>
            <div className="relative z-10">
              <Navigation />
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/generator" element={<Generator />} />
                <Route path="/analisi" element={<Analisi />} />
                <Route path="/intro" element={<Intro />} />
                <Route path="/features" element={<Features />} />
                <Route path="/pricing" element={<Pricing />} />
              </Routes>
            </div>
          </div>
        </HashRouter>
      </HelmetProvider>
    </ErrorBoundary>
  );
}

export default App;
