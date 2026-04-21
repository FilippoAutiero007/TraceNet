# TraceNet - Cisco Packet Tracer Network Generator

Generatore di reti Cisco Packet Tracer (.pkt) da linguaggio naturale con interfaccia web.

![TraceNet Screenshot](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-19-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
## 🌐 Cos'è TraceNet

TraceNet è uno strumento full-stack che converte descrizioni in linguaggio naturale in file `.pkt` compatibili con **Cisco Packet Tracer 8.x**. Basta descrivere la rete desiderata ("2 router, 3 switch, 10 PC con OSPF e VLAN") e TraceNet genera automaticamente:

- Il file `.pkt` pronto da aprire in Packet Tracer
- Le configurazioni IOS complete per ogni dispositivo
- Il calcolo VLSM ottimizzato delle sottoreti
- Un file XML di debug della topologia generata
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


## 📄 License

MIT License - vedi [LICENSE](LICENSE) per dettagli.


