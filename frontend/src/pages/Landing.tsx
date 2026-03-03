import { Hero } from '@/sections/Hero';
import { Features } from '@/sections/Features';
import { Pricing } from '@/sections/Pricing';
import { Dashboard } from '@/sections/Dashboard';
import { Footer } from '@/sections/Footer';
import { SEOHead } from '@/components/SEOHead';

export function Landing() {
  return (
    <>
      <SEOHead />
      <main>
        <Hero />
        <Features />
        <Pricing />
        <Dashboard />
      </main>
      <Footer />
    </>
  );
}
