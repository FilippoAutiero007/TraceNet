import { useState } from 'react';
import { FileUp, CheckCircle, XCircle, AlertCircle, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@clerk/clerk-react';
import { Footer } from '@/sections/Footer';

export function Analisi() {
  const { isSignedIn } = useAuth();
  const [exerciseText, setExerciseText] = useState('');

  return (
    <div className="min-h-screen">
      <section className="relative py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mb-6">
              Analisi File .pkt
            </h1>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto">
              Carica un file Packet Tracer e ottieni una review tecnica dettagliata
            </p>
          </div>

          {!isSignedIn ? (
            <Card className="bg-slate-900/50 border-slate-800 p-8 text-center">
              <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Funzione riservata al piano Pro
              </h2>
              <p className="text-slate-400 mb-6">
                Il tuo piano attuale non include la correzione avanzata dei file Packet Tracer importati.
              </p>
              <Button className="bg-cyan-500 hover:bg-cyan-600 text-white">
                Accedi o Registrati
              </Button>
            </Card>
          ) : (
            <div className="space-y-8">
              <Card className="bg-slate-900/50 border-slate-800 p-8">
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    Seleziona un file Packet Tracer
                  </h2>
                  <p className="text-slate-400 text-sm">
                    Formato supportato: <span className="text-cyan-400">.pkt</span>
                  </p>
                </div>

                <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-cyan-500/50 transition-colors cursor-pointer">
                  <Upload className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
                  <p className="text-slate-300 mb-2">
                    Trascina il file qui o clicca per selezionare
                  </p>
                  <p className="text-slate-500 text-sm">
                    Massimo 10MB
                  </p>
                </div>

                <div className="mt-6">
                  <label className="block text-white font-medium mb-2">
                    Testo esercizio opzionale
                  </label>
                  <textarea
                    className="w-full h-32 bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                    placeholder="Puoi lasciare solo il .pkt oppure aggiungere anche la consegna: es. 'realizza due VLAN, routing OSPF e DHCP centralizzato...'"
                    value={exerciseText}
                    onChange={(e) => setExerciseText(e.target.value)}
                  />
                  <p className="text-slate-500 text-sm mt-2">
                    Modalità supportate: solo .pkt oppure .pkt + testo dell'esercizio
                  </p>
                </div>

                <Button className="w-full mt-6 bg-cyan-500 hover:bg-cyan-600 text-white py-4 text-lg">
                  <FileUp className="w-5 h-5 mr-2" />
                  Correggi file .pkt
                </Button>
              </Card>

              <Card className="bg-slate-900/50 border-slate-800 p-8">
                <h3 className="text-xl font-bold text-white mb-6">
                  Cosa include la correzione:
                </h3>
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300">
                      Elenco delle correzioni necessarie
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300">
                      Punti già corretti
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300">
                      Confronto opzionale con la consegna dell'esercizio
                    </span>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </div>
      </section>
      <Footer />
    </div>
  );
}