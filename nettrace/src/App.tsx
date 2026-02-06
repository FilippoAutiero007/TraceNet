import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navigation } from '@/components/Navigation';
import { Landing } from '@/pages/Landing';
import { Generator } from '@/pages/Generator';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <Navigation />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/generator" element={<Generator />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
