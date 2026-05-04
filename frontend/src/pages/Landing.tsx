import { Hero } from '@/sections/Hero';
import { Footer } from '@/sections/Footer';
import { SEOHead } from '@/components/SEOHead';

export function Landing() {
  return (
    <>
      <SEOHead />
      <div className="flex flex-col">
        <Hero />
      </div>
      <Footer />
    </>
  );
}
