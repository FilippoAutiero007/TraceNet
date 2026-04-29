import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { Navigation } from '@/components/Navigation';
import { Landing } from '@/pages/Landing';
import { Generator } from '@/pages/Generator';
import { Intro } from '@/pages/Intro';
import { Features } from '@/pages/Features';
import { Pricing } from '@/pages/Pricing';
import { Free } from '@/pages/Free';
import { Pro } from '@/pages/Pro';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <HelmetProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-slate-950">
            <Navigation />
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/generator" element={<Generator />} />
              <Route path="/intro" element={<Intro />} />
              <Route path="/features" element={<Features />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/free" element={<Free />} />
              <Route path="/pro" element={<Pro />} />
            </Routes>
          </div>
        </BrowserRouter>
      </HelmetProvider>
    </ErrorBoundary>
  );
}

export default App;
