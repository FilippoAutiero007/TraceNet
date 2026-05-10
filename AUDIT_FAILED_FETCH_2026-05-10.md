# Audit `Failed to fetch` e problemi correlati

Data audit: 2026-05-10

Ambito:
- revisione statica del codice frontend, backend e configurazioni di deploy
- focus primario sul sintomo browser `TypeError: Failed to fetch`
- inclusione di altri problemi rilevanti emersi durante la scansione

Nota:
- i riferimenti di linea sono basati sullo stato attuale del branch `main`
- `Failed to fetch` nel browser non identifica una singola causa: puo indicare CORS, DNS/TLS, backend down, timeout client, preflight bloccato, abort locale, reverse proxy rotto

## 1. Cause possibili del `Failed to fetch`

### 1.1 Frontend: API base URL rigido verso Render

- File: [frontend/src/config.ts](frontend/src/config.ts)
  - Linee: 13-17
  - Dettaglio:
    - in produzione il fallback e `https://tracenet-api.onrender.com`
    - se `VITE_API_URL` non e valorizzata, tutto il frontend punta comunque a Render
  - Possibili effetti:
    - se il backend reale e stato spostato, rinominato, sospeso o ha DNS/SSL intermittente, il browser vede `Failed to fetch`
    - se il frontend e deployato su un dominio diverso ma `VITE_API_URL` non e coerente, il bug resta invisibile fino a runtime

### 1.2 Frontend: timeout client che termina localmente la richiesta

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 71, 133-147, 169-176
  - Dettaglio:
    - `REQUEST_TIMEOUT_MS = 180000`
    - `AbortController` abortisce localmente il `fetch`
  - Possibili effetti:
    - il browser puo finire nel catch come errore rete anche se il backend sta ancora lavorando
    - in presenza di cold start Render o job lenti la UX degrada in `Failed to fetch` / timeout anche se il backend non e crashato

### 1.3 Frontend: messaggio di rete generico che maschera cause diverse

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 279-287
  - Dettaglio:
    - `TypeError` con `fetch` viene trasformato in `Cannot connect to server...`
  - Possibili effetti:
    - CORS, abort client, DNS, TLS, proxy e backend spento vengono tutti appiattiti nello stesso messaggio
    - il debug lato utente diventa ambiguo

### 1.4 Frontend: retry auth opzionale solo nella pagina generator, non nel client condiviso

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 122-168
  - Dettaglio:
    - il retry senza token su `AUTH_PROVIDER_UNAVAILABLE` esiste solo qui
- File: [frontend/src/lib/api.ts](frontend/src/lib/api.ts)
  - Linee: 65-142
  - Dettaglio:
    - il client API condiviso usa `fetch` diretto senza retry opzionale, timeout o distinzione errori
  - Possibili effetti:
    - due parti del frontend possono comportarsi in modo diverso verso lo stesso backend
    - analisi `.pkt`, capabilities e altri endpoint possono ancora produrre errori rete non mitigati

### 1.5 Backend: CORS basato su allowlist esplicita e regex incompleta per domini futuri

- File: [backend/app/main.py](backend/app/main.py)
  - Linee: 111-123
- File: [backend/app/config.py](backend/app/config.py)
  - Linee: 36-46
  - Dettaglio:
    - CORS dipende da `allowed_origins` e da `origin_regex`
    - il regex copre solo preview Vercel `tracenet`/`nettrace`, non domini custom arbitrari
  - Possibili effetti:
    - un nuovo dominio frontend, staging o preview fuori naming convention puo fallire in preflight e produrre `Failed to fetch`
    - la fix richiede redeploy backend: aggiornare solo il frontend non basta

### 1.6 Docker Compose dev con allowlist piu stretta del backend applicativo

- File: [docker-compose.yml](docker-compose.yml)
  - Linee: 8-15
  - Dettaglio:
    - `ALLOWED_ORIGINS=http://localhost:5173`
  - Possibili effetti:
    - ambiente dev con `vite preview` su `4173` o altra porta puo avere `Failed to fetch` solo in Docker
    - incoerenza tra default dell'app e compose

### 1.7 Backend: auth opzionale ancora dipendente da Clerk se il token e formalmente invalido

- File: [backend/app/services/auth.py](backend/app/services/auth.py)
  - Linee: 151-162
  - Dettaglio:
    - `get_optional_auth_context()` degrada ad anonimo solo su `503`
    - token invalidi continuano a fallire
  - Possibili effetti:
    - se il browser manda token corrotti o token di ambiente sbagliato, endpoint anonimi possono comunque fallire
    - lato utente puo sembrare un errore rete o server quando il problema e il token

### 1.8 Backend: JWKS remoto come dipendenza runtime forte

- File: [backend/app/services/auth.py](backend/app/services/auth.py)
  - Linee: 37-56, 100-148
  - Dettaglio:
    - la validazione token dipende da `https://api.clerk.com/v1/jwks`
    - timeout client `httpx.AsyncClient(timeout=10.0)`
  - Possibili effetti:
    - latenza o indisponibilita Clerk introducono ritardi visibili nel percorso auth
    - se il browser invia token e il provider auth e lento, il backend puo sembrare instabile

### 1.9 Backend: cold start / piattaforma non visibili nel codice ma compatibili col sintomo

- File: [backend/Dockerfile](backend/Dockerfile)
  - Linee: 3-46
  - Dettaglio:
    - backend pensato per Render, con avvio via `uvicorn`
  - Possibili effetti:
    - `Failed to fetch` o timeout lato browser possono dipendere dal cold start del servizio Render
    - il codice locale risponde in pochi secondi ma il deploy sospeso puo impiegare molto di piu al primo hit

### 1.10 Backend: lock globale di generazione che serializza tutte le richieste

- File: [backend/app/routers/generate.py](backend/app/routers/generate.py)
  - Linee: 37, 181-190, 296-305
  - Dettaglio:
    - `_pkt_generation_lock = Lock()`
    - timeout lock a 30 secondi per generate e manual generate
  - Possibili effetti:
    - una sola generazione lenta puo bloccare tutte le altre
    - sotto concorrenza il frontend puo vedere attese lunghe seguite da `GENERATION_BUSY`, timeout client o user experience simile a backend down

### 1.11 Backend: generazione PKT dipendente da I/O filesystem e template decrypt

- File: [backend/app/services/pkt_generator/entrypoint.py](backend/app/services/pkt_generator/entrypoint.py)
  - Linee: 45-60
- File: [backend/app/services/pkt_generator/generator.py](backend/app/services/pkt_generator/generator.py)
  - Linee: 89-114, 122-259
  - Dettaglio:
    - lettura/decrypt template PKT
    - manipolazione XML completa
    - scrittura file `.pkt` e `.xml`
  - Possibili effetti:
    - su disco lento, container freddo o storage problematico il backend puo degradare molto
    - il browser non vede un errore applicativo finche il timeout client non scatta

### 1.12 Backend: quota anonima basata su IP client del proxy

- File: [backend/app/services/generation_quota.py](backend/app/services/generation_quota.py)
  - Linee: 34-38, 54-78
  - Dettaglio:
    - il subject anonimo e `request.client.host`
  - Possibili effetti:
    - dietro proxy/load balancer piu utenti possono condividere lo stesso IP
    - si possono vedere blocchi o comportamenti apparentemente casuali che l'utente scambia per errore rete

## 2. Punti che possono generare errori fuorvianti o diagnosi incomplete

### 2.1 Frontend generator non usa il client API condiviso

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 180-278
  - Problema:
    - la pagina implementa il proprio protocollo fetch/retry/timeout
- File: [frontend/src/lib/api.ts](frontend/src/lib/api.ts)
  - Linee: 65-142
  - Problema:
    - esiste un client API separato con logica diversa
  - Rischio:
    - drift funzionale tra schermate
    - bug fissati in un posto ma non nell'altro

### 2.2 Stato conversazionale frontend che puo fondere richieste distinte

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 89, 227-233, 263-277, 307-310
  - Problema:
    - `conversationState` e `pendingParse` influenzano il payload successivo
  - Rischio:
    - un utente puo credere di aver fatto una richiesta nuova, ma parte del contesto precedente puo ancora intervenire
    - output inatteso non uguale a input corrente

### 2.3 Fallback default client-side potenzialmente divergente dal backend

- File: [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
  - Linee: 64-70, 307-310
- File: [backend/app/services/nlp_parser.py](backend/app/services/nlp_parser.py)
  - Linee: 37-43, 201-202
  - Problema:
    - i default esistono sia lato frontend sia lato backend
  - Rischio:
    - drift tra valori di default se uno dei due cambia
    - bug difficili da diagnosticare in ambienti con deploy frontend/backend non sincronizzati

### 2.4 Healthcheck troppo superficiale rispetto ai problemi reali

- File: [backend/app/main.py](backend/app/main.py)
  - Linee: 126-133
  - Problema:
    - `/api/health` non verifica template PKT, output dir, Clerk, Mistral, lock contention o quota persistence
  - Rischio:
    - il servizio puo risultare `healthy` anche quando la generazione reale fallisce o resta lenta

## 3. Altri problemi non direttamente inerenti al `Failed to fetch`

### 3.1 API key Mistral esposta nel frontend

- File: [frontend/src/hooks/useMistral.ts](frontend/src/hooks/useMistral.ts)
  - Linee: 2-6
  - Problema:
    - il client Mistral viene istanziato nel browser con `VITE_MISTRAL_API_KEY`
  - Rischio:
    - esposizione credenziale lato client
    - uso improprio dell'API da parte di terzi
    - possibile conflitto con CSP o bundling

### 3.2 Pagina Analisi con UI quasi statica/non collegata

- File: [frontend/src/pages/Analisi.tsx](frontend/src/pages/Analisi.tsx)
  - Linee: 25-78
  - Problema:
    - la UI mostra upload e CTA, ma nel file non c'e nessun `fetch`/submit reale
  - Rischio:
    - UX rotta o fuorviante
    - l'utente interpreta l'assenza di azione come bug di rete

### 3.3 DownloadResult usa `window.open` diretto

- File: [frontend/src/components/DownloadResult.tsx](frontend/src/components/DownloadResult.tsx)
  - Linee: 35-37, 114-129
  - Problema:
    - download affidato a popup/tab esterni
  - Rischio:
    - popup blocker
    - comportamento incoerente tra browser
    - diagnosi piu difficile di 404/download falliti

### 3.4 Cache parser in-memory non condivisa e non persistente

- File: [backend/app/utils/cache.py](backend/app/utils/cache.py)
  - Linee: 10-73
- File: [backend/app/services/nlp_parser.py](backend/app/services/nlp_parser.py)
  - Linee: 292-303, 380-381
  - Problema:
    - cache solo in processo, non condivisa tra repliche
  - Rischio:
    - comportamento diverso tra istanze
    - invalidazione assente
    - risultato vecchio se la logica di parse cambia ma il processo resta vivo

### 3.5 Todo tecnico non allineato allo stato reale del router frontend

- File: [frontend/src/App.tsx](frontend/src/App.tsx)
  - Linee: 1, 18-35
- File: [frontend/vite.config.ts](frontend/vite.config.ts)
  - Linee: 6-8
  - Problema:
    - oggi l'app usa `HashRouter`, non `BrowserRouter`
  - Rischio:
    - parte della documentazione/backlog puo essere obsoleta e indirizzare fix non piu necessari

### 3.6 `useMistral` usa `useCallback` ovunque ma resta client-side e scollegato dal resto dell'app

- File: [frontend/src/hooks/useMistral.ts](frontend/src/hooks/useMistral.ts)
  - Linee: 8-68
  - Problema:
    - hook potenzialmente non usato e con responsabilita sensibili sul client
  - Rischio:
    - codice morto o semi-morto che complica audit sicurezza e CSP

### 3.7 Quota e contatori solo in memoria

- File: [backend/app/services/generation_quota.py](backend/app/services/generation_quota.py)
  - Linee: 24-25, 66-83
  - Problema:
    - stato quota perso a ogni restart e non condiviso
  - Rischio:
    - enforcement incoerente tra deploy e repliche

### 3.8 Log strutturati parziali ma niente timing su tutto il flusso app

- File: [backend/app/utils/logger.py](backend/app/utils/logger.py)
  - Linee: 10-34
- File: [backend/app/routers/generate.py](backend/app/routers/generate.py)
  - Linee: 95-112, 166-217
  - Problema:
    - logging utile ma ancora concentrato su pochi endpoint
  - Rischio:
    - root cause analysis lenta su problemi distribuiti tra auth, parser, output dir, template e rete

## 4. Riepilogo prioritario per il sintomo segnalato

Ordine di probabilita per `TypeError: Failed to fetch` / timeout nel browser:

1. `VITE_API_URL` o fallback `API_BASE_URL` puntano a un backend Render freddo, sospeso o non raggiungibile.
2. origine frontend non presente nella allowlist CORS del backend deployato.
3. backend deployato ma lento per cold start, lock globale o I/O di generazione PKT.
4. browser che invia token Clerk e backend che entra in percorso auth/Clerk degradato o intermittente.
5. timeout client-side che abortisce la richiesta e trasforma un backend lento in errore rete.
6. popup/download o schermate secondarie che usano percorsi differenti dal generator e falliscono senza diagnostica uniforme.

## 5. File piu rilevanti da controllare per primi in produzione

- [frontend/src/config.ts](frontend/src/config.ts)
- [frontend/src/pages/Generator.tsx](frontend/src/pages/Generator.tsx)
- [backend/app/main.py](backend/app/main.py)
- [backend/app/config.py](backend/app/config.py)
- [backend/app/services/auth.py](backend/app/services/auth.py)
- [backend/app/routers/generate.py](backend/app/routers/generate.py)
- [backend/app/services/pkt_generator/entrypoint.py](backend/app/services/pkt_generator/entrypoint.py)
- [backend/app/services/pkt_generator/generator.py](backend/app/services/pkt_generator/generator.py)
