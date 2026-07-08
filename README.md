# TraceNet - Cisco Packet Tracer Network Generator

> A full-stack tool that converts natural language descriptions into `.pkt` files compatible with Cisco Packet Tracer 8.x.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-19-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)

---

## 🌐 What is TraceNet?

TraceNet is a full-stack tool that converts natural language descriptions into `.pkt` files compatible with **Cisco Packet Tracer 8.x**. Simply describe the desired network (e.g., "2 routers, 3 switches, 10 PCs with OSPF and VLANs") and TraceNet automatically generates:

- The `.pkt` file ready to open in Packet Tracer
- Complete IOS configurations for every device
- Optimized VLSM subnet calculations
- An XML debug file of the generated topology

---

## 💥 Features

### Backend (Python + FastAPI)
- 🧠 **NLP Parsing:** Intelligent analysis of natural language descriptions using Mistral AI
- 📊 **Automatic VLSM:** Optimized subnet calculation with VLSM algorithm
- ⚙️ **IOS Configurations:** Automatic generation of complete Cisco configurations
- 🧱 **.pkt Export:** Binary files compatible with Cisco Packet Tracer 8.x
- 📶 **Routing Protocols:** Support for Static Routing, RIP, OSPF, and EIGRP

### Frontend (React + TypeScript)
- 🎨 **Modern UI:** Dark-themed interface built with Tailwind CSS and shadcn/ui
- 📋 **Predefined Templates:** 4+ ready-to-use templates for common scenarios
- 📱 **Responsive Layout:** Optimized design for desktop, tablet, and mobile devices
- ⚡ **Real-Time Feedback:** Loading states and error handling
- 🖵 **Direct Download:** Download `.pkt` and XML debug files directly

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI / NLP | Mistral AI |
| Frontend | React 19, TypeScript |
| Styling | Tailwind CSS, shadcn/ui |
| Networking | Cisco IOS, VLSM, OSPF, RIP, EIGRP |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/FilippoAutiero007/TraceNet.git
cd TraceNet
```

### 2. Backend setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🤝 Contributing

Contributions are welcome! TraceNet is a personal project that is still growing, and any help is greatly appreciated.

If you'd like to contribute:

1. **Fork** the repository
2. **Create** a new branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m 'Add your feature'`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open a Pull Request** and describe what you've done

You can also help by:
- 🐛 **Reporting bugs** via [Issues](https://github.com/FilippoAutiero007/TraceNet/issues)
- 💡 **Suggesting new features** or improvements
- ⭐ **Starring the repo** if you find it useful

> This project was born as a learning experience. Feedback and ideas from the community are the best way to make it grow!

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---
---

# TraceNet - Generatore di Reti Cisco Packet Tracer

> Uno strumento full-stack che converte descrizioni in linguaggio naturale in file `.pkt` compatibili con Cisco Packet Tracer 8.x.

---

## 🌐 Cos'è TraceNet?

TraceNet è uno strumento full-stack che converte descrizioni in linguaggio naturale in file `.pkt` compatibili con **Cisco Packet Tracer 8.x**. Basta descrivere la rete desiderata (es. "2 router, 3 switch, 10 PC con OSPF e VLAN") e TraceNet genera automaticamente:

- Il file `.pkt` pronto da aprire in Packet Tracer
- Le configurazioni IOS complete per ogni dispositivo
- Il calcolo VLSM ottimizzato delle sottoreti
- Un file XML di debug della topologia generata

---

## 💥 Funzionalità

### Backend (Python + FastAPI)
- 🧠 **NLP Parsing:** Analisi intelligente delle descrizioni in linguaggio naturale con Mistral AI
- 📊 **VLSM Automatico:** Calcolo ottimizzato dei sottoreti con algoritmo VLSM
- ⚙️ **Configurazioni IOS:** Generazione automatica di configurazioni Cisco complete
- 🧱 **Export .pkt:** File binari compatibili con Cisco Packet Tracer 8.x
- 📶 **Protocolli di Routing:** Supporto per Static, RIP, OSPF, EIGRP

### Frontend (React + TypeScript)
- 🎨 **UI Moderna:** Interfaccia dark theme con Tailwind CSS e shadcn/ui
- 📋 **Template Predefiniti:** 4+ template pronti all'uso per scenari comuni
- 📱 **Layout Responsive:** Design ottimizzato per desktop, tablet e mobile
- ⚡ **Real-time Feedback:** Stati di caricamento e gestione errori
- 🖵 **Download Diretto:** Scarica file .pkt e XML debug

---

## 🛠️ Stack Tecnologico

| Livello | Tecnologia |
|---|---|
| Backend | Python, FastAPI |
| AI / NLP | Mistral AI |
| Frontend | React 19, TypeScript |
| Stile | Tailwind CSS, shadcn/ui |
| Networking | Cisco IOS, VLSM, OSPF, RIP, EIGRP |

---

## 🚀 Come Iniziare

### 1. Clona il repository
```bash
git clone https://github.com/FilippoAutiero007/TraceNet.git
cd TraceNet
```

### 2. Avvia il backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Avvia il frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🤝 Contribuire al Progetto

I contributi sono benvenuti! TraceNet è un progetto personale ancora in crescita e qualsiasi aiuto è apprezzato.

Se vuoi contribuire:

1. **Fai il fork** del repository
2. **Crea** un nuovo branch (`git checkout -b feature/tua-feature`)
3. **Committa** le modifiche (`git commit -m 'Aggiungi la tua feature'`)
4. **Pusha** il branch (`git push origin feature/tua-feature`)
5. **Apri una Pull Request** descrivendo cosa hai fatto

Puoi anche aiutare:
- 🐛 **Segnalando bug** tramite le [Issues](https://github.com/FilippoAutiero007/TraceNet/issues)
- 💡 **Proponendo nuove funzionalità** o miglioramenti
- ⭐ **Mettendo una stella al repo** se lo trovi utile

> Questo progetto nasce come esperienza di apprendimento. Il feedback e le idee della community sono il modo migliore per farlo crescere!

---

## 📄 Licenza

Licenza MIT - vedi [LICENSE](./LICENSE) per i dettagli.
