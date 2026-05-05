# TraceNet Todo List (rev 2)

Stato: backlog tecnico allineato al codice attuale, organizzato per area e priorità.
Obiettivo: mantenere TraceNet robusto (backend), consistente (frontend), sicuro (security) e pronto a deploy reali (DevOps/DX).

---

## Backend

### High

- **Retry del parser solo su errori veramente transienti**
  - Oggi `@retry` in `nlp_parser.py` prende anche `Exception`, quindi ritenta anche errori deterministici già mappati in `ParserServiceError`.
  - Task:
    - Limitare il retry a un set di eccezioni transitorie (timeout HTTP, errori di rete, rate limit provider AI).
    - Escludere esplicitamente errori di schema/JSON malformato dal retry.
    - Aggiungere test che verificano che un output AI malformato non venga ritentato tre volte.

- **Gestione chiara delle reti base /31 e /32**
  - `_default_subnet_for_base()` gestisce male le reti troppo piccole usando `max(1, num_addresses - 2)`, mentre la VLSM richiede almeno 4 indirizzi allocabili.
  - Task:
    - Rifiutare in ingresso reti base non compatibili con la VLSM con un errore 4xx esplicito.
    - Allineare comportamento e messaggi tra `generate.py` e `subnet_calculator.py`.
    - Aggiungere test per /31 e /32 con messaggi di errore chiari.

- **Pulizia e coerenza di `/generate-pkt`**
  - In `generate.py` `network_config_dict` ha chiavi duplicate (`server_services`) e la summary usa `request.routing_protocol` invece del valore normalizzato (`protocol_value`).
  - Task:
    - Rimuovere chiavi duplicate dal dict, garantendo un solo punto di verità.
    - Usare sempre il protocollo normalizzato nella summary e nei log.
    - Aggiungere un test di integrazione che controlla la coerenza tra request, summary e pipeline interna.

- **Allineare il flusso manuale al flusso automatico**
  - `ManualNetworkRequest` non espone alcune opzioni (es. `nat`) che invece passano dal flusso automatico in `generate.py`.
  - Task:
    - Estendere gli schema manuali per includere tutte le opzioni supportate dal flusso automatico (NAT, ACL avanzate, ecc.).
    - Aggiungere test che confrontano l'output di scenari equivalenti automatico vs manuale.

- **Quota di generazione settimanale persistente e multi-istanza**
  - L'attuale contatore quota vive nel processo API e si resetta a ogni riavvio; in multi-replica ogni istanza tiene contatori separati.
  - Task:
    - Spostare il contatore su storage condiviso (es. Redis/Postgres) con chiave `user_id + week`.
    - Rendere configurabile la quota per piano (free vs pro).
    - Aggiungere test di integrazione sulla logica di quota.

- **Autorizzazione basata su Clerk per ogni richiesta costosa**
  - Per ogni chiamata agli endpoint di generazione, inviare il token utente (Clerk) e verificare piano (free/pro) + quota.
  - Task:
    - Introdurre un middleware FastAPI che valida il token Clerk (via `auth.py`) e recupera l'`user_id` per quota e permessi.
    - Rendere obbligatoria l'autenticazione per gli endpoint di generazione, con fallback chiaro per gli anonimi.
    - Aggiungere test per percorsi: utente free con quota residua, quota esaurita, utente pro, token mancante/invalid.

- **Hardening della pipeline AI/NLP**
  - Un output AI buggato da Mistral può propagare errori strani attraverso `nlp_parser.py`.
  - Task:
    - Introdurre validazione di schema forte sul JSON AI prima di toccare servizi interni.
    - Definire classi di errore specifiche (schema error, semantic error, AI timeout).
    - Log strutturati con request id per diagnosi.

---

### Medium

- **Test di integrazione non più skip-friendly di default**
  - Alcuni test saltano in assenza di template `.pkt` o fixture, rendendo verde la suite in ambienti incompleti.
  - Task:
    - In CI ufficiale: trattare l'assenza di template/fixture come errore di setup (fallire, non skippare).
    - Mantenere lo skip solo in dev dietro flag/env (es. `TRACENET_ALLOW_PKT_TEST_SKIP=1`).

- **Completare i test placeholder**
  - `test_template_path_resolution()` in `test_pkt_catalog.py` è ancora un `pass`.
  - Task:
    - Verificare la risoluzione dei path dei template e fallire se la struttura cambia.
    - Aggiungere almeno un caso di test per ogni tipo di template supportato.

- **Ampliare la coverage delle service class principali**
  - Servizi critici con logica non banale: `auth.py`, `generation_quota.py`, `pkt_analyzer.py`, `pkt_crypto.py`, `pkt_review.py`, `pkt_xml_builder.py`, `rag_knowledge.py`, `subnet_calculator.py`.
  - Task:
    - Aggiungere test unitari per i path normali e per gli errori (errori di decrypt, RAG vuoto, errori di subnet).
    - Misurare coverage e fissare una soglia minima in CI.

- **Test API end-to-end sugli endpoint principali**
  - Endpoint chiave: `/api/parse-network-request`, `/api/generate-pkt`, `/api/generate-pkt-manual`.
  - Task:
    - Testare i codici 2xx/4xx/5xx con payload realistici.
    - Verificare messaggi di errore user-friendly (senza `str(exc)` raw verso il client).

---

### Low

- **Migrazione degli hook di lifecycle FastAPI**
  - `main.py` usa ancora `@app.on_event("startup")`, deprecato e rumoroso nei test.
  - Task:
    - Migrare a `lifespan` o nuovi hook consigliati da FastAPI.
    - Aggiungere un test che verifica l'inizializzazione corretta.

- **Pulizia e typing**
  - Task:
    - Uniformare type hints, docstring e messaggi di log nei moduli backend.
    - Aggiornare `schema.json` se cambiano gli schema Pydantic.

---

## Frontend

### High

- **Rendere deterministico `Hero`**
  - `Hero.tsx` genera particelle e proprietà (size, opacity, delay) con `Math.random()` in fase di render, rendendo il componente non puro.
  - Task:
    - Spostare la generazione in `useMemo` o in init deterministica (seed fisso o set predefinito).
    - Aggiungere test che verificano la riproducibilità dell'output.

- **Rendere deterministico `SidebarMenuSkeleton`**
  - `SidebarMenuSkeleton` calcola la width con `Math.random()` dentro `useMemo`.
  - Task:
    - Definire una lista finita di width possibili e selezionarle in modo deterministico.
    - Aggiungere test sul layout dello skeleton.

- **Allineare Router e Vite per deploy reali**
  - `vite.config.ts` usa `base: './'`, mentre `App.tsx` usa `BrowserRouter`, creando problemi su refresh diretto / subpath senza rewrite.
  - Task:
    - Decidere strategia: `BrowserRouter` + rewrite lato server, oppure `HashRouter` o `basename` coerente.
    - Documentare in README frontend come configurare il deploy.

- **Gestione robusta di `ClerkProvider`**
  - `main.tsx` monta `ClerkProvider` anche se `VITE_CLERK_PUBLISHABLE_KEY` è assente/undefined.
  - Task:
    - Validare la key a runtime in dev: se manca, mostrare un errore esplicito e non montare l'app.
    - In produzione: loggare in modo strutturato e fail-fast se la key non è configurata.

---

### Medium

- **Implementare l'azione del pulsante "Guarda la Demo"**
  - Il bottone nella Hero oggi è un controllo morto.
  - Task:
    - Collegare il bottone a una pagina demo interna (es. template precaricato) oppure a un video/tutorial esterno.
    - Testare che il CTA sia accessibile e funzioni su mobile e desktop.

- **Percorso unico tra pagine HTML statiche e SPA React**
  - Il frontend ha HTML statici (`features.html`, `pricing.html`, `free.html`, `pro.html`, ecc.) più la SPA sotto `src/`.
  - Task:
    - Decidere se mantenere gli HTML statici come landing marketing o migrare tutto nella SPA.
    - Allineare copy e layout tra versioni per evitare divergenza.

- **Test di routing e auth**
  - Task:
    - Integrare e2e test (Cypress/Playwright) che coprono: login con Clerk, creazione rete via linguaggio naturale, creazione rete manuale, download del `.pkt`, comportamento con quota esaurita.

---

### Low

- **Hardening tooling frontend**
  - Task:
    - Raffinare config ESLint + TypeScript per intercettare side-effect (es. `no-math-random-in-render`).
    - Aggiungere script npm per lint/test/format unificati (es. `npm run ci`).
    - Valutare Storybook per documentare i componenti principali.

---

## Security

### High

- **Limiti espliciti sui payload JSON e liste configurabili**
  - Task:
    - Aggiungere validazioni centralizzate sugli schema (numero subnet, ACL rules, VLAN, record DNS, lunghezza stringhe libere).
    - Restituire 4xx con messaggi chiari quando i limiti vengono superati.

- **Rate limiting sugli endpoint più costosi**
  - Endpoint candidati: `/api/parse-network-request`, `/api/generate-pkt`, `/api/generate-pkt-manual`.
  - Task:
    - Implementare rate limit per IP e per utente autenticato, parametrizzato per piano (free/pro).
    - Aggiungere metriche e log sul throttling.

- **Separare errori client-facing dai dettagli interni**
  - In diversi punti il backend manda ancora `str(exc)` verso il client.
  - Task:
    - Introdurre un livello di mapping eccezioni → codici + messaggi safe.
    - Loggare dettagli tecnici solo lato server (con request id).

- **Validazione più rigida dei campi con `extra="allow"`**
  - Aree: NAT, ACL, VLAN.
  - Task:
    - Definire whitelist di chiavi ammesse.
    - Rifiutare input con chiavi sconosciute, evitando configurazioni ambigue.

---

### Medium

- **Timeout e budget di esecuzione**
  - Task:
    - Impostare timeout lato servizio e lato request per chiamate AI e generazione `.pkt`.
    - Restituire 5xx controllati al client in caso di timeout, con log di contesto.

- **Isolamento e cleanup degli artefatti**
  - Task:
    - Usare directory per-request (es. `OUTPUT_DIR/<request_id>/`).
    - Aggiungere job periodico per cancellare file più vecchi di N ore/giorni, con retention differenziata free vs pro.

- **Sandboxizzazione della generazione PKT**
  - Task:
    - Valutare subprocess dedicato, worker separato o container isolato per la generazione.
    - Introdurre time limit e limiti di risorse (CPU/RAM) per job di generazione.

---

## DevOps / Infra

### High

- **Pipeline CI completa (GitHub Actions)**
  - Task:
    - Job backend: installare dipendenze, lanciare test (inclusi quelli che richiedono template `.pkt` e fixture) e fallire in caso di setup incompleto.
    - Job frontend: lint + test + build di produzione.
    - Job sicurezza: static analysis base (es. bandit) e controllo `.env.example`.

- **Build e publish immagini Docker**
  - Sono presenti `docker-compose.yml`, `backend/Dockerfile` e `frontend/Dockerfile.dev`.
  - Task:
    - Definire Dockerfile di produzione per il frontend.
    - Aggiungere workflow per build/tag/push automatico delle immagini su registry (Docker Hub/GHCR).
    - Documentare i comandi di deploy.

---

### Medium

- **Osservabilità**
  - Task:
    - Introdurre log strutturati (JSON) lato backend con request id, user id e tipo di errore.
    - Integrare metriche base (conteggio richieste, tempi di risposta, errori 4xx/5xx) per endpoint di generazione.

- **Config e `.env.example`**
  - Task:
    - Aggiornare `.env.example` includendo tutte le chiavi richieste (chiavi AI, Clerk, storage quota).
    - Documentare nel README come configurare un ambiente dev vs prod.

---

## DX / Documentazione

### Medium

- **Migliorare QUICKSTART e README**
  - Esistono `README.md` root e `QUICKSTART.txt`, oltre a `backend/PKT_GENERATION.md`.
  - Task:
    - Unire/collegare meglio QUICKSTART e README con: setup veloce in locale (dev), setup da zero con Docker, esempi di prompt di input.
    - Linkare da README a `PKT_GENERATION.md` per chi vuole capire i dettagli di generazione.

- **Schema API pubblico**
  - Task:
    - Esportare automaticamente lo schema OpenAPI di FastAPI e documentare gli endpoint principali.
    - Aggiungere esempi di richieste (curl/HTTPie) per ogni endpoint.
