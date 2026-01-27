import { useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { 
  Activity, 
  Network, 
  Play, 
  Pause, 
  RotateCcw,
  Download,
  BarChart3,
  Layers,
  Zap,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { useMistral } from '@/hooks/useMistral';

interface Packet {
  id: string;
  source: string;
  destination: string;
  protocol: string;
  size: number;
  timestamp: number;
  status: 'sent' | 'received' | 'dropped';
}

interface Node {
  id: string;
  type: 'router' | 'switch' | 'endpoint';
  x: number;
  y: number;
  label: string;
}

interface Link {
  from: string;
  to: string;
  delay: number;
  bandwidth: number;
}

export function Dashboard() {
  const { isSignedIn } = useAuth();
  const { analyzeNetwork, isLoading } = useMistral();
  const [isSimulating, setIsSimulating] = useState(false);
  const [speed, setSpeed] = useState(50);
  const [packets, setPackets] = useState<Packet[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<string>('');

  // Mock network data
  const nodes: Node[] = [
    { id: 'router1', type: 'router', x: 400, y: 200, label: 'Router 1' },
    { id: 'pc1', type: 'endpoint', x: 200, y: 100, label: 'PC 1' },
    { id: 'pc2', type: 'endpoint', x: 600, y: 100, label: 'PC 2' },
    { id: 'pc3', type: 'endpoint', x: 200, y: 300, label: 'PC 3' },
    { id: 'pc4', type: 'endpoint', x: 600, y: 300, label: 'PC 4' },
  ];

  const links: Link[] = [
    { from: 'pc1', to: 'router1', delay: 10, bandwidth: 1000 },
    { from: 'pc2', to: 'router1', delay: 10, bandwidth: 1000 },
    { from: 'pc3', to: 'router1', delay: 15, bandwidth: 500 },
    { from: 'pc4', to: 'router1', delay: 15, bandwidth: 500 },
  ];

  const stats = {
    packetsSent: 1250,
    packetsReceived: 1245,
    packetsDropped: 5,
    avgLatency: 12.5,
    throughput: 850,
    activeConnections: 4,
  };

  const handleStartSimulation = () => {
    setIsSimulating(true);
    // Simulate packet generation
    const interval = setInterval(() => {
      const newPacket: Packet = {
        id: Math.random().toString(36).substr(2, 9),
        source: ['pc1', 'pc2', 'pc3', 'pc4'][Math.floor(Math.random() * 4)],
        destination: 'router1',
        protocol: ['TCP', 'UDP', 'ICMP'][Math.floor(Math.random() * 3)],
        size: Math.floor(Math.random() * 1000) + 64,
        timestamp: Date.now(),
        status: Math.random() > 0.02 ? 'received' : 'dropped',
      };
      setPackets(prev => [newPacket, ...prev].slice(0, 50));
    }, 1000 / (speed / 10));

    return () => clearInterval(interval);
  };

  const handleStopSimulation = () => {
    setIsSimulating(false);
  };

  const handleAnalyzeWithAI = async () => {
    const networkConfig = JSON.stringify({ nodes, links, stats });
    const analysis = await analyzeNetwork(networkConfig);
    if (analysis) {
      setAiAnalysis(String(analysis));
    }
  };

  if (!isSignedIn) {
    return (
      <section id="dashboard" className="py-24 bg-slate-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Dashboard di Simulazione
            </h2>
            <p className="text-slate-400 max-w-2xl mx-auto mb-8">
              Accedi per accedere alla dashboard completa e iniziare a simulare le tue reti.
            </p>
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12">
              <Network className="w-16 h-16 text-cyan-400 mx-auto mb-6" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Accedi per Continuare
              </h3>
              <p className="text-slate-500 mb-6">
                La dashboard è disponibile solo per utenti registrati.
              </p>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="dashboard" className="py-24 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white mb-2">Dashboard</h2>
          <p className="text-slate-400">Simula e analizza le tue reti in tempo reale</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {[
            { label: 'Pacchetti Inviati', value: stats.packetsSent, icon: Activity },
            { label: 'Pacchetti Ricevuti', value: stats.packetsReceived, icon: Activity },
            { label: 'Persi', value: stats.packetsDropped, icon: AlertCircle },
            { label: 'Latenza Media', value: `${stats.avgLatency}ms`, icon: Zap },
            { label: 'Throughput', value: `${stats.throughput} Mbps`, icon: BarChart3 },
            { label: 'Connessioni', value: stats.activeConnections, icon: Layers },
          ].map((stat, index) => (
            <Card key={index} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <stat.icon className="w-5 h-5 text-cyan-400 mb-2" />
                <div className="text-2xl font-bold text-white">{stat.value}</div>
                <div className="text-xs text-slate-500">{stat.label}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Network Visualization */}
          <div className="lg:col-span-2">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-white">Topologia di Rete</CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant={isSimulating ? 'destructive' : 'default'}
                    onClick={isSimulating ? handleStopSimulation : handleStartSimulation}
                  >
                    {isSimulating ? (
                      <Pause className="w-4 h-4 mr-2" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    {isSimulating ? 'Pausa' : 'Avvia'}
                  </Button>
                  <Button size="sm" variant="outline">
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* Speed Control */}
                <div className="flex items-center gap-4 mb-4">
                  <span className="text-sm text-slate-400">Velocità:</span>
                  <Slider
                    value={[speed]}
                    onValueChange={(value) => setSpeed(value[0])}
                    max={100}
                    step={10}
                    className="w-48"
                  />
                  <span className="text-sm text-slate-400">{speed}%</span>
                </div>

                {/* Network Canvas */}
                <div className="relative h-96 bg-slate-950 rounded-lg overflow-hidden">
                  <svg className="w-full h-full">
                    {/* Links */}
                    {links.map((link, index) => {
                      const fromNode = nodes.find(n => n.id === link.from);
                      const toNode = nodes.find(n => n.id === link.to);
                      if (!fromNode || !toNode) return null;
                      return (
                        <line
                          key={index}
                          x1={fromNode.x}
                          y1={fromNode.y}
                          x2={toNode.x}
                          y2={toNode.y}
                          stroke="#334155"
                          strokeWidth="2"
                        />
                      );
                    })}
                    
                    {/* Nodes */}
                    {nodes.map((node) => (
                      <g key={node.id}>
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r="30"
                          fill={selectedNode === node.id ? '#06b6d4' : '#1e293b'}
                          stroke="#334155"
                          strokeWidth="2"
                          className="cursor-pointer hover:stroke-cyan-400 transition-colors"
                          onClick={() => setSelectedNode(node.id)}
                        />
                        <text
                          x={node.x}
                          y={node.y + 50}
                          textAnchor="middle"
                          fill="#94a3b8"
                          fontSize="12"
                        >
                          {node.label}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            {/* Packet Log */}
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-lg">Log Pacchetti</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-48 overflow-y-auto space-y-2">
                  {packets.length === 0 ? (
                    <p className="text-slate-500 text-sm text-center py-8">
                      Nessun pacchetto. Avvia la simulazione.
                    </p>
                  ) : (
                    packets.map((packet) => (
                      <div
                        key={packet.id}
                        className="flex items-center justify-between p-2 bg-slate-800 rounded text-sm"
                      >
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            packet.status === 'received' ? 'bg-green-400' : 'bg-red-400'
                          }`} />
                          <span className="text-slate-300">{packet.protocol}</span>
                        </div>
                        <span className="text-slate-500">{packet.size}B</span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* AI Analysis */}
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-lg">Analisi AI</CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={handleAnalyzeWithAI}
                  disabled={isLoading}
                  className="w-full mb-4 bg-purple-500 hover:bg-purple-600"
                >
                  {isLoading ? 'Analisi in corso...' : 'Analizza con AI'}
                </Button>
                {aiAnalysis && (
                  <div className="p-3 bg-slate-800 rounded-lg text-sm text-slate-300 max-h-48 overflow-y-auto">
                    {aiAnalysis}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Export */}
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white text-lg">Esporta</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Button variant="outline" className="w-full justify-start">
                    <Download className="w-4 h-4 mr-2" />
                    Esporta PCAP
                  </Button>
                  <Button variant="outline" className="w-full justify-start">
                    <Download className="w-4 h-4 mr-2" />
                    Esporta JSON
                  </Button>
                  <Button variant="outline" className="w-full justify-start">
                    <Download className="w-4 h-4 mr-2" />
                    Esporta CSV
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
