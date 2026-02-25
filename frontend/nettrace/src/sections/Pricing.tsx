import { Check, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SignUpButton } from '@clerk/clerk-react';

const clerkEnabled = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const PRO_FEATURES = [
  'Unlimited nodes',
  'Unlimited projects',
  'All topologies',
  'Priority support',
  'PCAP, JSON, CSV export',
  'Advanced AI analysis',
  'Full API access',
];

export function Pricing() {
  return (
    <section id="pricing" className="py-24 bg-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Simple, Transparent Pricing</h2>
          <p className="text-slate-400 max-w-xl mx-auto">One plan. All features. Free updates included.</p>
        </div>

        <div className="flex justify-center">
          <div className="relative rounded-2xl p-8 bg-gradient-to-b from-cyan-500/15 to-slate-900 border-2 border-cyan-500 w-full max-w-sm shadow-xl shadow-cyan-500/10">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span className="bg-cyan-500 text-white text-xs font-semibold px-4 py-1 rounded-full">Most Popular</span>
            </div>

            <div className="mb-6">
              <div className="p-2.5 rounded-lg bg-cyan-500/15 w-fit mb-4">
                <Sparkles className="w-8 h-8 text-cyan-400" aria-hidden="true" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-1">Pro</h3>
              <p className="text-slate-400 text-sm">For professionals and teams</p>
            </div>

            <div className="mb-7">
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-white">€14.99</span>
                <span className="text-slate-400 text-sm">/month</span>
              </div>
              <p className="text-slate-500 text-xs mt-1">or €149.99 / year — save 17%</p>
            </div>

            <ul className="space-y-3 mb-8">
              {PRO_FEATURES.map((feature) => (
                <li key={feature} className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-cyan-400 flex-shrink-0" aria-hidden="true" />
                  <span className="text-slate-200 text-sm">{feature}</span>
                </li>
              ))}
            </ul>

            {clerkEnabled ? (
              <SignUpButton mode="modal">
                <Button className="w-full bg-cyan-500 hover:bg-cyan-400 text-white font-semibold py-5 shadow-lg shadow-cyan-500/20 focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900">
                  Get Started with Pro
                </Button>
              </SignUpButton>
            ) : (
              <Button className="w-full bg-cyan-500 hover:bg-cyan-400 text-white font-semibold py-5" disabled>
                Get Started with Pro
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
