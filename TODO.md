# TraceNet Todo List

Stato: backlog tecnico aggiornato al codice attuale.  
Contiene solo bug o ottimizzazioni reali ancora aperte, divisi per area e priorità.  
Le voci già risolte sono state rimosse.

---

## Backend

### High

- **Heuristica `_is_network_related()` troppo banale**
  - Usa solo `any(keyword in lowered ...)` in [`nlp_parser.py`](backend/app/services/nlp_parser.py).
  - Richieste borderline possono essere classificate male prima del parser NLP vero.
  - Fix: ampliare i pattern (es. regex per CIDR, keyword su routing/VLAN/NAT); valutare un piccolo punteggio euristico.

- **Messaggio di errore parser degradato perso nel frontend**
  - Il backend può restituire `error="NLP Service Unavailable: Mistral API Key missing on server."` in [`ParseNetworkResponse`](backend/app/services/nlp_parser.py).
  - In [`Generator.tsx`](frontend/src/pages/Generator.tsx) quando `intent === "incomplete"` il frontend mostra solo i campi mancanti e scarta `parseData.error`.
  - In ambienti senza chiave AI l'utente vede un errore parziale e non capisce che il parser NLP è disabilitato.
  - Fix: includere `parseData.error` nel messaggio UI oppure mostrarlo separatamente come backend-status warning.

---

### Medium

- **Test di integrazione skip-friendly invece di gate duro**
  - [`test_pkt_generator_integration.py`](backend/tests/test_pkt_generator_integration.py) e [`test_layout.py`](backend/tests/test_layout.py) saltano se mancano template `.pkt` in `backend/templates/`.
  - [`test_pkt_link_metadata.py`](backend/tests/test_pkt_link_metadata.py) salta se mancano fixture in `backend/tests/fixtures/`.
  - In ambienti incompleti la suite può risultare verde senza aver esercitato i percorsi critici.
  - Fix: in CI ufficiale trattare l'assenza di template/fixture come errore di setup (fallire, non skippare). Mantenere lo skip solo in dev via flag/env var.

- **Test placeholder in `test_pkt_catalog.py`**
  - [`test_pkt_catalog.py`](backend/tests/test_pkt_catalog.py) contiene `test_template_path_resolution()` con solo `pass`.
  - La suite dichiara copertura su quel punto ma non controlla niente.
  - Fix: implementare un test minimo che verifichi la risoluzione corretta dei path template e fallisca se la struttura cambia.

---

### Low

- **`@app.on_event("startup")` deprecato in `main.py`**
  - [`main.py`](backend/app/main.py) emette warning durante i test.
  - Non è un bug funzionale oggi, ma rende la suite più rumorosa.
  - Fix: migrare ai nuovi hook lifecycle FastAPI (`lifespan` o equivalenti).

---

## Frontend

### High

- **`Hero` usa `Math.random()` durante il render**
  - In [`Hero.tsx`](frontend/src/sections/Hero.tsx) particelle, size, opacity e animation delay vengono generati on-render.
  - Render non puro: in Strict Mode i valori possono cambiare tra render consecutivi, rendendo l'UI instabile.
  - Fix: spostare la generazione in `useMemo` / `useEffect` legati al mount, o pre-calcolare i pattern.

- **`SidebarMenuSkeleton` usa `Math.random()` per la width**
  - In [`sidebar.tsx`](frontend/src/components/ui/sidebar.tsx) la width nasce da `Math.random()` dentro `useMemo`.
  - Il componente non è deterministicamente riproducibile tra mount diversi.
  - Fix: rendere le width deterministiche (set fisso di valori o seed stabile).

- **Router + Vite incoerenti per deploy statici / subpath**
  - [`vite.config.ts`](frontend/vite.config.ts) usa `base: './'`; [`App.tsx`](frontend/src/App.tsx) usa `BrowserRouter`.
  - Su refresh diretto o deploy statici senza rewrite coerenti il routing può rompersi.
  - Fix: allineare la strategia — `BrowserRouter` + rewrite lato server, oppure `HashRouter` / `basename` coerente con `base` di Vite.

- **`ClerkProvider` montato anche senza publishable key**
  - [`main.tsx`](frontend/src/main.tsx) passa `VITE_CLERK_PUBLISHABLE_KEY` direttamente a `ClerkProvider`, che può essere `undefined`.
  - In ambienti mal configurati il bootstrap fallisce in modo poco chiaro.
  - Fix: validare la key prima di montare `ClerkProvider`; mostrare un errore esplicito in dev se assente.

---

### Medium

- **Bottone "Guarda la Demo" senza azione**
  - In [`Hero.tsx`](frontend/src/sections/Hero.tsx) il bottone non ha onClick / navigazione.
  - L'interfaccia promette un'azione che non esiste.
  - Fix: collegare a una route di demo interna, un link esterno, o rimuovere finché non esiste una demo reale.

---

### Low

- **Suite frontend non copre purezza e bootstrap**
  - I problemi noti (`Hero`, `SidebarMenuSkeleton`, router, `ClerkProvider`) non hanno test automatici dedicati.
  - Future modifiche possono introdurre regressioni senza localizzazione rapida.
  - Fix: aggiungere test su determinismo dei componenti, routing su path chiave, comportamento con Clerk key mancante.

---

## Security

- **Limitare dimensione massima dei payload JSON e delle liste configurabili**
  - Limitare numero di elementi per lista (subnet, ACL rules, VLAN, record DNS, utenti mail) e lunghezza delle stringhe libere.
  - Non limitare i prefix IP: tutte le reti da `/1` a `/32` restano ammesse.
  - Restituire errori 4xx chiari in caso di superamento.

- **Rate limiting sugli endpoint costosi**
  - Candidati: `/api/parse-network-request`, `/api/generate-pkt`, `/api/generate-pkt-manual`.
  - Middleware di rate limiting per IP e/o per utente autenticato, parametrizzato per piano (free/pro).

- **Separare errori client-facing dai dettagli interni**
  - In più punti il backend ritorna ancora `str(exc)` nel payload.
  - Introdurre un modello uniforme di error response (codice errore + messaggio generico + request id).
  - Loggare i dettagli solo lato server, mai nel payload.

- **Validazione più rigida dei campi `extra="allow"`**
  - Aree candidate: NAT, ACL, VLAN.
  - Introdurre whitelist di chiavi ammesse; rifiutare esplicitamente input con chiavi sconosciute.

- **Timeout espliciti e budget di esecuzione sulle generazioni PKT**
  - Impostare timeout su chiamate AI e su fase di generazione/salvataggio PKT.
  - Restituire errori 5xx con messaggio controllato in caso di timeout.

- **Isolamento degli output e artefatti temporanei per richiesta**
  - Usare directory per-request (es. `request_id` o `user_id + timestamp`).
  - Evitare che due richieste concorrenti scrivano sullo stesso path.

- **Cleanup automatico e retention limitata in `OUTPUT_DIR`**
  - Job periodico che elimina file più vecchi di N ore/giorni.
  - Possibile differenziazione retention free vs pro.

- **Log di sicurezza con request id e classificazione errori**
  - Includere sempre `request_id` nei log e nelle risposte di errore.
  - Classificare errori (es. `SEC_RATE_LIMIT`, `SEC_PAYLOAD_TOO_LARGE`, `SEC_INVALID_SCHEMA`).

- **Esecuzione PKT in processo / sandbox separata**
  - Valutare subprocess isolato, container/worker separato o coda di job con time limit e risorse limitate.
  - Ridurre l'impatto di input malevoli o bug del generatore sul processo API principale.

- **Autenticazione Clerk e quota generazione reti**
  - Per ogni richiesta al webservice, inviare il token utente Clerk (bearer / session token).
  - Backend: validare il token con le chiavi pubbliche Clerk, estrarre l'id utente e il piano (free/pro).
  - Tenere un contatore per utente e settimana (`user_id`, `week`, `generated_count`).
  - Utenti free: limite di 10 reti generate per settimana; superato il limite, rispondere con 402/429 + messaggio chiaro.
  - Utenti pro: nessun limite (o limite superiore configurabile).
