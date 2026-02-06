# TraceNet - Cisco Packet Tracer Network Generator

Generatore di reti Cisco Packet Tracer (.pkt) da linguaggio naturale con interfaccia web moderna.

![TraceNet Screenshot](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-19-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)

## 🌟 Funzionalità

### Backend (Python + FastAPI)
- 🧠 **NLP Parsing**: Analisi intelligente delle descrizioni in linguaggio naturale con Mistral AI
- 📊 **VLSM Automatico**: Calcolo ottimizzato dei sottoreti con algoritmo VLSM
- ⚙️ **Configurazioni IOS**: Generazione automatica di configurazioni Cisco complete
- 📦 **Export .pkt**: File binari compatibili con Cisco Packet Tracer 8.x
- 🔄 **Protocolli di Routing**: Supporto per Static, RIP, OSPF, EIGRP

### Frontend (React + TypeScript)
- 🎨 **UI Moderna**: Interfaccia dark theme con Tailwind CSS e shadcn/ui
- 📝 **Template Predefiniti**: 4+ template pronti all'uso per scenari comuni
- 🖼️ **Layout Responsive**: Design ottimizzato per desktop, tablet e mobile
- ⚡ **Real-time Feedback**: Stati di caricamento e gestione errori
- 📥 **Download Diretto**: Scarica file .pkt e XML debug

## 🏗️ Architettura

```
TraceNet/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   │   └── generate.py
│   │   ├── services/     # Business logic
│   │   │   ├── nlp_parser.py
│   │   │   ├── subnet_calculator.py
│   │   │   ├── pkt_generator.py
│   │   │   └── pkt_file_generator.py
│   │   └── main.py
│   ├── requirements.txt
│   └── server.py
│
└── nettrace/             # React Frontend
    ├── src/
    │   ├── pages/
    │   │   ├── Landing.tsx
    │   │   └── Generator.tsx
    │   ├── components/
    │   │   ├── NetworkInput.tsx
    │   │   ├── DownloadResult.tsx
    │   │   ├── Navigation.tsx
    │   │   └── ui/         # shadcn/ui components
    │   └── sections/       # Landing page sections
    └── package.json
```

## 🚀 Installazione e Avvio

### Prerequisiti
- **Python 3.10+**
- **Node.js 18+**
- **npm o pnpm**
- **Mistral AI API Key** ([ottienila qui](https://console.mistral.ai/))

### 1. Clone del Repository

```bash
git clone https://github.com/FilippoAutiero007/TraceNet.git
cd TraceNet
```

### 2. Setup Backend

```bash
cd backend

# Crea ambiente virtuale (opzionale ma consigliato)
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa dipendenze
pip install fastapi uvicorn mistralai python-dotenv

# Crea file .env con la tua API key
cp .env.example .env
nano .env  # Aggiungi MISTRAL_API_KEY=tua_chiave_qui

# Avvia il server (porta 8001)
python server.py
```

Il backend sarà disponibile su: `http://localhost:8001`

### 3. Setup Frontend

```bash
cd ../nettrace

# Installa dipendenze
npm install

# Crea file .env (usa le impostazioni default)
cp .env.example .env

# Avvia il dev server (porta 5173)
npm run dev
```

Il frontend sarà disponibile su: `http://localhost:5173`

## 📖 Utilizzo

### Interfaccia Web

1. **Accedi al Generator**: Vai su `http://localhost:5173` e clicca su "Try Generator"
2. **Scegli un Template**: Clicca su uno dei 4 template predefiniti o scrivi la tua descrizione
3. **Genera la Rete**: Clicca su "Generate Network" e attendi 5-10 secondi
4. **Scarica il File**: Clicca su "Download .pkt File" e apri con Cisco Packet Tracer

### API REST

#### Endpoint: `POST /api/generate-pkt`

```bash
curl -X POST http://localhost:8001/api/generate-pkt \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "✅ File .pkt generato con successo!",
  "pkt_download_url": "/api/download/network_20250206_153000.pkt",
  "xml_download_url": "/api/download/network_20250206_153000.xml",
  "config_summary": {
    "base_network": "192.168.0.0/24",
    "subnets_count": 2,
    "routers": 1,
    "switches": 2,
    "pcs": 70,
    "routing_protocol": "static"
  },
  "subnets": [...]
}
```

#### Download File

```bash
curl -O http://localhost:8001/api/download/network_20250206_153000.pkt
```

## 🎯 Template Predefiniti

### 1. Small Office Network
```
Create network with 2 VLANs: 
- Admin (20 hosts)
- Guest (50 hosts)
Using: Static routing
```

### 2. Corporate Campus
```
Network with 3 buildings:
- Building_A (100 hosts)
- Building_B (50 hosts)
- Building_C (25 hosts)
Using: OSPF
```

### 3. Data Center
```
Data center with:
- DMZ (5 servers)
- Production (50 hosts)
- Management (10 hosts)
Using: EIGRP
```

### 4. School Network
```
School network with:
- Labs (100 hosts)
- Teachers (30 hosts)
- Admin (10 hosts)
- Guests (50 hosts)
Using: RIP
```

## 🛠️ Tecnologie Utilizzate

### Backend
- **FastAPI**: Framework web asincrono ad alte prestazioni
- **Mistral AI**: LLM per parsing del linguaggio naturale
- **Pydantic**: Validazione dati con type hints
- **Python-dotenv**: Gestione variabili d'ambiente

### Frontend
- **React 19**: Libreria UI con hooks moderni
- **TypeScript**: Type safety e autocompletamento
- **Vite**: Build tool veloce per sviluppo
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: Componenti UI accessibili e personalizzabili
- **React Router**: Routing client-side
- **Lucide React**: Icone moderne

## 📝 API Documentation

Quando il backend è in esecuzione, visita:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## 🔧 Configurazione

### Backend Environment Variables

```bash
# backend/.env
MISTRAL_API_KEY=your_mistral_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/nettrace
ENVIRONMENT=development
OUTPUT_DIR=/tmp/tracenet
```

### Frontend Environment Variables

```bash
# nettrace/.env
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

## 🐛 Troubleshooting

### Backend non si avvia
```bash
# Verifica che tutte le dipendenze siano installate
pip install fastapi uvicorn mistralai python-dotenv

# Verifica che la porta 8001 sia libera
lsof -i :8001
```

### Frontend mostra errore di connessione
```bash
# Verifica che il backend sia in esecuzione su porta 8001
curl http://localhost:8001/api/health

# Se il backend usa una porta diversa, aggiorna .env
echo "VITE_API_URL=http://localhost:PORTA" > nettrace/.env
```

### File .pkt non si apre in Packet Tracer
- Assicurati di usare **Cisco Packet Tracer 8.x** o superiore
- Verifica che il file non sia corrotto (deve essere un GZIP valido)
- Scarica il file XML debug per analizzare la struttura

## 📄 License

MIT License - vedi [LICENSE](LICENSE) per dettagli.

## 👨‍💻 Autore

**Filippo Autiero**
- GitHub: [@FilippoAutiero007](https://github.com/FilippoAutiero007)
- Repository: [TraceNet](https://github.com/FilippoAutiero007/TraceNet)

## 🤝 Contributi

I contributi sono benvenuti! Per favore:
1. Forka il repository
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Committa i cambiamenti (`git commit -m 'Add AmazingFeature'`)
4. Pusha sul branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📚 Roadmap

- [ ] Autenticazione utenti con Clerk
- [ ] Salvataggio configurazioni nel database
- [ ] Visualizzazione grafica della topologia di rete
- [ ] Export in altri formati (EVE-NG, GNS3)
- [ ] Supporto per configurazioni avanzate (ACL, NAT, VPN)
- [ ] Template marketplace condiviso dalla community

## 🙏 Ringraziamenti

- **Mistral AI** per il modello NLP
- **shadcn/ui** per i componenti UI
- **FastAPI** per il framework backend
- **Cisco** per Packet Tracer
