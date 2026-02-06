import { Hero } from '@/sections/Hero';
import { Features } from '@/sections/Features';
import { Pricing } from '@/sections/Pricing';
import { Dashboard } from '@/sections/Dashboard';
import { Footer } from '@/sections/Footer';

export function Landing() {
  return (
    <>
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
