import { useState } from 'react';
import { Network, Cpu, BarChart3, FileCode } from 'lucide-react';

const features = [
  { id: 'simulation', icon: Network, title: 'Network Simulation', description: 'Build and simulate complex networks with customizable topologies.', details: ['Topologies: Mesh, Star, Bus, Ring', 'Drag-and-drop configuration', 'Custom parameters (delay, bandwidth, packet loss)', 'Multiple project support'] },
  { id: 'tracing', icon: Cpu, title: 'Packet Tracing', description: 'Trace every packet through the network in real time.', details: ['Packet path visualization', 'Precise timestamps', 'Header analysis at each hop', 'Error and loss highlighting'] },
  { id: 'analysis', icon: BarChart3, title: 'Advanced Analysis', description: 'Get detailed insights into network performance.', details: ['Real-time statistics', 'Latency and throughput metrics', 'Charts and visualizations', 'Cross-simulation comparison'] },
  { id: 'export', icon: FileCode, title: 'Data Export', description: 'Export results in multiple formats for external analysis.', details: ['PCAP format (Wireshark-compatible)', 'JSON for API integrations', 'CSV for spreadsheet analysis', 'Automated PDF reports'] },
];

export function Features() {
  const [activeFeature, setActiveFeature] = useState('simulation');

  return (
    <section id="features" className="py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Powerful Features for Professionals</h2>
          <p className="text-slate-400 max-w-2xl mx-auto">Everything you need to simulate, trace and analyze complex networks — in one intuitive tool.</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          <div className="space-y-3">
            {features.map((feature) => (
              <button
                key={feature.id}
                className={`w-full p-5 rounded-xl text-left transition-all focus-visible:ring-2 focus-visible:ring-cyan-500 ${
                  activeFeature === feature.id ? 'bg-cyan-500/10 border border-cyan-500/30' : 'bg-slate-900/50 border border-slate-800 hover:border-slate-700'
                }`}
                onClick={() => setActiveFeature(feature.id)}
                aria-pressed={activeFeature === feature.id}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 rounded-lg ${activeFeature === feature.id ? 'bg-cyan-500/20' : 'bg-slate-800'}`}>
                    <feature.icon className={`w-5 h-5 ${activeFeature === feature.id ? 'text-cyan-400' : 'text-slate-400'}`} aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-white mb-0.5">{feature.title}</h3>
                    <p className="text-slate-400 text-sm">{feature.description}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8">
            {features.map((feature) => activeFeature === feature.id && (
              <div key={feature.id}>
                <div className="flex items-center gap-3 mb-5">
                  <feature.icon className="w-7 h-7 text-cyan-400" aria-hidden="true" />
                  <h3 className="text-xl font-bold text-white">{feature.title}</h3>
                </div>
                <ul className="space-y-3">
                  {feature.details.map((d) => (
                    <li key={d} className="flex items-center gap-3 text-slate-300 text-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 flex-shrink-0" aria-hidden="true" />
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
