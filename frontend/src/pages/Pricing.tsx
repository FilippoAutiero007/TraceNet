import { AlertCircle, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function Pricing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black pt-24 pb-12">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <div className="w-24 h-24 bg-cyan-500/20 rounded-full flex items-center justify-center mx-auto mb-8">
          <AlertCircle className="w-12 h-12 text-cyan-400" />
        </div>
        <h1 className="text-5xl sm:text-6xl font-extrabold text-white mb-6">
          In fase di lavorazione
        </h1>
        <p className="text-xl text-slate-400 max-w-lg mx-auto mb-10">
          Stiamo lavorando per offrirti i migliori prezzi. Torna presto per scoprire le nostre offerte!
        </p>
        <Button
          size="lg"
          className="bg-cyan-500 hover:bg-cyan-600 text-white px-10 py-7 text-xl"
          onClick={() => navigate('/')}
        >
          <Home className="w-6 h-6 mr-3" />
          Torna alla Home
        </Button>
      </div>
    </div>
  );
}