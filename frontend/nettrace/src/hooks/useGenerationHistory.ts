import { useState, useCallback } from 'react';

export interface HistoryEntry {
  id: string;
  description: string;
  timestamp: number;
  result: unknown;
}

const STORAGE_KEY = 'nettrace_generation_history';
const MAX_ENTRIES = 3;

function load(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function useGenerationHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(load);

  const addEntry = useCallback((description: string, result: unknown) => {
    const entry: HistoryEntry = { id: Date.now().toString(), description, timestamp: Date.now(), result };
    setHistory((prev) => {
      const next = [entry, ...prev].slice(0, MAX_ENTRIES);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  return { history, addEntry };
}
