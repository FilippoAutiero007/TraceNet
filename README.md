# TraceNet - Network Packet Tracing Tool

TraceNet è una piattaforma avanzata per la simulazione e la visualizzazione di topologie di rete e traffico pacchetti.

## Struttura del Progetto

Il progetto è suddiviso in tre componenti principali:

- **`/nettrace`**: Frontend React 18 con Cytoscape.js per la visualizzazione interattiva della rete e Tailwind CSS per l'interfaccia utente.
- **`/backend`**: API REST basata su Node.js/Express e TypeScript per la gestione di utenti, progetti e simulazioni.
- **`/engine`**: Motore di simulazione core scritto in Python (utilizzando Scapy) per la logica di routing e gestione pacchetti.

## Requisiti

- Node.js 18+
- Python 3.10+
- PostgreSQL (per il backend)

## Installazione

### Frontend
```bash
cd nettrace
npm install
npm run dev
```

### Backend
```bash
cd backend
npm install
npm run dev
```

### Simulation Engine
```bash
cd engine
pip install scapy
python network_engine.py
```

## Funzionalità Implementate

- [x] Visualizzazione interattiva con Cytoscape.js
- [x] Dashboard di monitoraggio in tempo reale
- [x] Motore di simulazione pacchetti (Python)
- [x] Boilerplate API Backend (Express/TS)
- [x] Supporto per diverse topologie di rete
