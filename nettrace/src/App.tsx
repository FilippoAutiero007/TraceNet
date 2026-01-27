import { Navigation } from '@/components/Navigation';
import { Hero } from '@/sections/Hero';
import { Features } from '@/sections/Features';
import { Pricing } from '@/sections/Pricing';
import { Dashboard } from '@/sections/Dashboard';
import { Footer } from '@/sections/Footer';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-slate-950">
      <Navigation />
      <main>
        <Hero />
        <Features />
        <Pricing />
        <Dashboard />
      </main>
      <Footer />
    </div>
  );
}

export default App;
