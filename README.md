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




TraceNet - Cisco Packet Tracer Network Generator

A Cisco Packet Tracer (.pkt) network generator from natural language with a web interface.

🌐 What is TraceNet?

TraceNet is a full-stack tool that converts natural language descriptions into .pkt files compatible with Cisco Packet Tracer 8.x. Simply describe the desired network ("2 routers, 3 switches, 10 PCs with OSPF and VLANs"), and TraceNet automatically generates:

A .pkt file ready to open in Packet Tracer
Complete IOS configurations for every device
Optimized VLSM subnet calculations
An XML debug file of the generated topology
🌟 Features
Backend (Python + FastAPI)
🧠 NLP Parsing: Intelligent analysis of natural language descriptions using Mistral AI
📊 Automatic VLSM: Optimized subnet calculation with a VLSM algorithm
⚙️ IOS Configurations: Automatic generation of complete Cisco configurations
📦 .pkt Export: Binary files compatible with Cisco Packet Tracer 8.x
🔄 Routing Protocols: Support for Static Routing, RIP, OSPF, and EIGRP
Frontend (React + TypeScript)
🎨 Modern UI: Dark-themed interface built with Tailwind CSS and shadcn/ui
📝 Predefined Templates: 4+ ready-to-use templates for common scenarios
🖼️ Responsive Layout: Optimized design for desktop, tablet, and mobile devices
⚡ Real-Time Feedback: Loading states and error handling
📥 Direct Download: Download .pkt and XML debug files directly
📄 License

MIT License – see LICENSE for details.
