import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Play, Square, Plus, Settings, Activity, Download, Pause, RotateCcw } from 'lucide-react';
import { useNetworkSimulation } from '@/hooks/useNetworkSimulation';
import { Slider } from '@/components/ui/slider';

export function Dashboard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const { nodes, links, isSimulating, startSimulation, stopSimulation } = useNetworkSimulation();
  const [speed, setSpeed] = useState(50);

  useEffect(() => {
    if (!containerRef.current) return;

    const elements = [
      ...nodes.map(n => ({ data: { id: n.id, label: n.label, type: n.type } })),
      ...links.map(l => ({ data: { source: l.source, target: l.target } }))
    ];

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#1e293b',
            'label': 'data(label)',
            'color': '#94a3b8',
            'text-valign': 'bottom',
            'text-margin-y': 10,
            'width': 40,
            'height': 40,
            'border-width': 2,
            'border-color': '#334155',
            'font-size': '12px'
          }
        },
        {
          selector: 'node[type="router"]',
          style: {
            'background-color': '#0f172a',
            'shape': 'rectangle'
          }
        },
        {
          selector: 'node[type="host"]',
          style: {
            'background-color': '#06b6d4',
            'shape': 'ellipse'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: {
        name: 'grid',
        rows: 1
      }
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [nodes, links]);

  return (
    <section id="dashboard" className="py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8 flex justify-between items-end">
          <div>
            <h2 className="text-3xl font-bold text-white mb-2">Dashboard di Simulazione</h2>
            <p className="text-slate-400">Simula e analizza le tue reti in tempo reale con Cytoscape.js</p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={isSimulating ? 'destructive' : 'default'}
              onClick={isSimulating ? stopSimulation : startSimulation}
              className={!isSimulating ? "bg-cyan-500 hover:bg-cyan-600" : ""}
            >
              {isSimulating ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {isSimulating ? 'Pausa' : 'Avvia'}
            </Button>
            <Button size="sm" variant="outline" className="border-slate-800 text-slate-400">
              <RotateCcw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Latenza Media', value: '12.5ms', icon: Activity, color: 'text-cyan-400' },
            { label: 'Packet Loss', value: '0.02%', icon: Activity, color: 'text-red-400' },
            { label: 'Throughput', value: '850 Mbps', icon: Activity, color: 'text-green-400' },
            { label: 'Nodi Attivi', value: nodes.length.toString(), icon: Activity, color: 'text-purple-400' },
          ].map((stat, index) => (
            <Card key={index} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className={`p-2 rounded-lg bg-slate-800 ${stat.color}`}>
                  <stat.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">{stat.label}</p>
                  <p className="text-xl font-bold text-white">{stat.value}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Network Visualization */}
          <div className="lg:col-span-2">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800 mb-4">
                <CardTitle className="text-white">Topologia di Rete</CardTitle>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-500">Velocità:</span>
                  <Slider
                    value={[speed]}
                    onValueChange={(v) => setSpeed(v[0])}
                    max={100}
                    step={10}
                    className="w-32"
                  />
                  <Button variant="ghost" size="icon" className="text-slate-400">
                    <Settings className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div ref={containerRef} className="h-[500px] bg-slate-950 rounded-lg overflow-hidden" />
              </CardContent>
            </Card>
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-lg">Log Pacchetti</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-48 overflow-y-auto space-y-2">
                  <p className="text-slate-500 text-sm text-center py-8">
                    {isSimulating ? 'In ascolto sul traffico...' : 'Avvia la simulazione per vedere i pacchetti.'}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-lg">Azioni Rapide</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start border-slate-800 text-slate-400">
                  <Plus className="w-4 h-4 mr-2" /> Aggiungi Nodo
                </Button>
                <Button variant="outline" className="w-full justify-start border-slate-800 text-slate-400">
                  <Download className="w-4 h-4 mr-2" /> Esporta Configurazione
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
