import { lazy, Suspense } from 'react';
import { Hero } from '@/sections/Hero';

const Features = lazy(() => import('@/sections/Features').then((m) => ({ default: m.Features })));
const Pricing = lazy(() => import('@/sections/Pricing').then((m) => ({ default: m.Pricing })));
const Footer = lazy(() => import('@/sections/Footer').then((m) => ({ default: m.Footer })));

export function Landing() {
  return (
    <>
      <main>
        <Hero />
        <Suspense fallback={<div className="min-h-[200px] bg-slate-950" />}>
          <Features />
        </Suspense>
        <Suspense fallback={<div className="min-h-[200px] bg-slate-900" />}>
          <Pricing />
        </Suspense>
      </main>
      <Suspense fallback={null}>
        <Footer />
      </Suspense>
    </>
  );
}
