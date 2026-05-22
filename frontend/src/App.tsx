import { HashRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { Navigation } from '@/components/Navigation';
import { Landing } from '@/pages/Landing';
import { Generator } from '@/pages/Generator';
import { Intro } from '@/pages/Intro';
import { Features } from '@/pages/Features';
import { Analisi } from '@/pages/Analisi';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import Galaxy from '@/components/Galaxy';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <HelmetProvider>
        <HashRouter>
          <div className="relative">
            <div className="fixed inset-0 z-0">
              <Galaxy
                starSpeed={0.5}
                density={1}
                hueShift={140}
                speed={0.3}
                glowIntensity={0.3}
                saturation={0}
                mouseRepulsion
                repulsionStrength={12}
                twinkleIntensity={0.3}
                rotationSpeed={0.05}
                transparent
              />
            </div>
            <div className="relative z-10">
              <Navigation />
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/generator" element={<Generator />} />
                <Route path="/analisi" element={<Analisi />} />
                <Route path="/intro" element={<Intro />} />
                <Route path="/features" element={<Features />} />
              </Routes>
            </div>
          </div>
        </HashRouter>
      </HelmetProvider>
    </ErrorBoundary>
  );
}

export default App;
