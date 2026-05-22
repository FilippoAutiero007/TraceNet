import { useState } from 'react';
import { Button } from '@/components/ui/button'; 
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Upload, Play, Download, Activity, Zap, Shield, Users } from 'lucide-react';

export function Free() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const handleAnalysis = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      setIsAnalyzing(false);
      setAnalysisComplete(true);
    }, 3000);
  };

  const features = [
    { icon: Activity, title: '1.000 Pacchetti', description: 'Analisi fino a 1.000 pacchetti per sessione' },
    { icon: Zap, title: 'Simulazioni Base', description: 'Simulazioni di rete standard' },
    { icon: Shield, title: 'Sicuro', description: 'Ambiente sandbox isolato' },
    { icon: Users, title: 'Community', description: 'Supporto della community' }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <Badge className="mb-4 bg-cyan-500/10 text-cyan-400 border-cyan-500/20">
              Versione Gratuita
            </Badge>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
              Analisi di Rete Gratuita
            </h1>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto mb-8">
              Inizia subito ad analizzare i tuoi pacchetti di rete. Nessuna carta di credito richiesta.
            </p>
          </div>

          {/* Analysis Tool */}
          <Card className="bg-slate-900/50 border-slate-800 max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="text-2xl text-white">Strumento di Analisi</CardTitle>
              <CardDescription className="text-slate-400">
                Carica i tuoi dati o avvia una simulazione per iniziare
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center hover:border-cyan-500/50 transition-colors">
                  <Upload className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
                  <p className="text-slate-300 mb-2">Trascina qui i tuoi file PCAP</p>
                  <p className="text-slate-500 text-sm mb-4">o</p>
                  <Button variant="outline" className="border-slate-300 text-black hover:bg-slate-200">
                    Scegli File
                  </Button>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-800"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 bg-black text-slate-500">o</span>
                  </div>
                </div>

                <div className="space-y-4">
                  <Input
                    placeholder="Indirizzo IP di destinazione (es. 192.168.1.1)"
                    className="bg-slate-800/50 border-slate-700 text-white placeholder-slate-500"
                  />
                  <Input
                    placeholder="Porta (es. 80, 443, 22)"
                    className="bg-slate-800/50 border-slate-700 text-white placeholder-slate-500"
                  />
                  <Input
                    placeholder="Protocollo (TCP, UDP, ICMP)"
                    className="bg-slate-800/50 border-slate-700 text-white placeholder-slate-500"
                  />
                </div>

                <Button
                  size="lg"
                  className="w-full bg-cyan-500 hover:bg-cyan-600 text-white py-6 text-lg"
                  onClick={handleAnalysis}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <Activity className="w-5 h-5 mr-2 animate-spin" />
                      Analisi in corso...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5 mr-2" />
                      Inizia Analisi Gratuita
                    </>
                  )}
                </Button>
              </div>

              {analysisComplete && (
                <div className="p-6 rounded-lg bg-green-500/10 border border-green-500/20">
                  <h3 className="text-lg font-semibold text-green-400 mb-2">Analisi Completata!</h3>
                  <p className="text-slate-300 mb-4">
                    Analizzati con successo 1.000 pacchetti.
                  </p>
                  <div className="flex gap-4">
                    <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800">
                      <Download className="w-4 h-4 mr-2" />
                      Scarica CSV
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Free Features */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-white text-center mb-16">
            Cosa Include la Versione Gratuita
          </h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {features.map((feature, index) => (
              <Card key={index} className="bg-slate-900/50 border-slate-800 hover:border-cyan-500/50 transition-colors">
                <CardContent className="p-6 text-center">
                  <feature.icon className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          </div>
      </section>


    </div>
  );
}
