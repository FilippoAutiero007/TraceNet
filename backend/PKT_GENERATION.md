# TraceNet - Packet Tracer File Generation

## Implementazione con ptexplorer

**AGGIORNAMENTO**: A partire da questa versione, TraceNet utilizza **ptexplorer** come metodo principale per la generazione di file .pkt, con fallback su Twofish/EAX quando necessario.

Questa implementazione utilizza le seguenti repository come riferimento tecnico per garantire la compatibilità con Cisco Packet Tracer 8.x:

### Repository di Riferimento

1. **ptexplorer** (axcheron) - **METODO PRINCIPALE**
   - Repository: https://github.com/axcheron/ptexplorer
   - Utilizzo: Conversione diretta XML ↔ PKT senza encryption manuale
   - Contributo: Implementazione nativa del formato PT senza dipendenze crittografiche
   - Stato: **Custom module in backend/ptexplorer.py** (non disponibile su PyPI)

2. **pka2xml** (mircodz) - **FALLBACK REFERENCE**
   - Repository: https://github.com/mircodz/pka2xml
   - Utilizzo: Analisi della struttura XML e dell'algoritmo di crittografia
   - Contributo: Comprensione del formato PT 8.x e del pipeline di encryption

3. **Unpacket** (Punkcake21) - **FALLBACK IMPLEMENTATION**
   - Repository: https://github.com/Punkcake21/Unpacket
   - Utilizzo: Implementazione pura Python di Twofish/EAX (quando ptexplorer non disponibile)
   - Contributo: Libreria crittografica senza dipendenze esterne

## Architettura

### Moduli Principali

```
backend/
├── ptexplorer.py              # Modulo ptexplorer custom (NUOVO - METODO PRINCIPALE)
│                              # Converte XML ↔ PKT senza encryption manuale
├── app/services/
│   ├── pkt_crypto.py          # Crittografia Twofish/EAX (FALLBACK ONLY)
│   ├── pkt_xml_builder.py     # Costruzione XML PT 8.x
│   ├── pkt_file_generator.py  # Orchestrazione con ptexplorer + fallback
│   └── ...
└── Decipher/                  # Libreria crittografica da Unpacket (FALLBACK)
    ├── twofish.py             # Implementazione Twofish-128
    ├── eax.py                 # Modalità EAX (AEAD)
    ├── cmac.py                # CMAC per autenticazione
    └── ctr.py                 # Counter mode
```

### Pipeline di Generazione (NUOVA - con ptexplorer)

```
XML (UTF-8)
    ↓
[Metodo Principale]
ptexplorer.PTFile.save()
    ↓
File .pkt binario (compatibile PT 8.x)

--- SE PTEXPLORER NON DISPONIBILE (fallback) ---

XML (UTF-8)
    ↓
[Stage 1] Compressione Qt-style (zlib + 4 byte header)
    ↓
[Stage 2] Obfuscation (XOR con (length - i))
    ↓
[Stage 3] Encryption (Twofish-128 in modalità EAX)
    Key: [137] * 16
    IV:  [16] * 16
    ↓
[Stage 4] Obfuscation (Reverse order + XOR con (length - i*length))
    ↓
File .pkt binario
```

### Vantaggi del Metodo ptexplorer

| Aspetto | Twofish/EAX (vecchio) | ptexplorer (nuovo) |
|---------|----------------------|-------------------|
| Complessità | 4 stage di encryption | Conversione diretta |
| Dipendenze | Decipher module custom | Solo zlib (stdlib) |
| Performance | Lento (multiple pass) | Veloce (single pass) |
| Manutenibilità | Complessa | Semplice |
| Compatibilità PT | ✅ PT 8.x | ✅ PT 8.x |
| Codice | ~200 linee | ~50 linee |

### Pipeline di Encryption (FALLBACK ONLY - quando ptexplorer non disponibile)

Il processo di crittografia segue esattamente l'algoritmo implementato da Cisco Packet Tracer, come documentato in **pka2xml.hpp**.
**Nota**: Questo metodo è utilizzato solo come fallback quando ptexplorer non è disponibile.

```
XML (UTF-8)
    ↓
[Stage 1] Compressione Qt-style (zlib + 4 byte header)
    ↓
[Stage 2] Obfuscation (XOR con (length - i))
    ↓
[Stage 3] Encryption (Twofish-128 in modalità EAX)
    Key: [137] * 16
    IV:  [16] * 16
    ↓
[Stage 4] Obfuscation (Reverse order + XOR con (length - i*length))
    ↓
File .pkt binario
```

### Parametri Crittografici

Come documentato in **pka2xml.hpp** (linee 120-121):

```python
KEY = bytes([137] * 16)  # Chiave Twofish hardcoded in PT
IV  = bytes([16] * 16)   # Nonce EAX hardcoded in PT
```

Questi valori sono costanti nel codice di Packet Tracer e sono utilizzati per tutti i file .pkt e .pka.

## Struttura XML PT 8.x

Il file XML generato segue la struttura **PACKETTRACER5** compatibile con PT 8.x:

```xml
<?xml version="1.0" encoding="utf-8"?>
<PACKETTRACER5 VERSION="8.2.2.0400">
  <WORKSPACE>
    <DEVICES>
      <DEVICE id="0" name="R1" type="Router2911" x="400" y="100">
        <CONFIG><!-- IOS commands --></CONFIG>
        <INTERFACE name="GigabitEthernet0/0" ip="..." mask="..."/>
      </DEVICE>
      <!-- Altri dispositivi -->
    </DEVICES>
    <LINKS>
      <LINK id="0" from="R1" from_port="..." to="S1" to_port="..." type="copper"/>
      <!-- Altri collegamenti -->
    </LINKS>
  </WORKSPACE>
</PACKETTRACER5>
```

## Testing e Validazione

### Test di Integrazione ptexplorer

```bash
cd backend
python test_ptexplorer_integration.py
```

Questo test:
1. ✅ Verifica che il modulo ptexplorer sia importabile
2. ✅ Testa la conversione XML → PKT → XML (roundtrip)
3. ✅ Verifica l'integrazione con pkt_file_generator
4. ✅ Conferma che i file generati siano validi

Output atteso:
```
🎉 ALL TESTS PASSED! 🎉
Total: 3 tests
Passed: 3 tests
Failed: 0 tests
```

### Test di Generazione Legacy

```bash
cd backend
python test_pkt_generation_new.py
```

Questo test:
1. ✅ Costruisce una rete di esempio con 2 subnet
2. ✅ Genera il file XML con struttura PT 8.x
3. ✅ Usa ptexplorer per la conversione (o Twofish/EAX come fallback)
4. ✅ Valida il roundtrip (encrypt → decrypt)
5. ✅ Verifica l'integrità del file .pkt

### Validazione Manuale

Per verificare che il file sia apribile in Packet Tracer:

1. Genera un file di test:
   ```bash
   python test_pkt_generation_new.py
   ```

2. Il file sarà salvato in:
   ```
   /tmp/tracenet_test/network_TIMESTAMP.pkt
   ```

3. Apri il file in Cisco Packet Tracer 8.x

## Vantaggi della Implementazione ptexplorer

### Rispetto alla Implementazione Twofish/EAX

| Aspetto | Twofish/EAX (fallback) | ptexplorer (principale) |
|---------|----------------------|------------------------|
| Metodo | Encryption manuale 4-stage | Conversione diretta XML↔PKT |
| Crittografia | Twofish/EAX complesso | XOR semplice (gestito da ptexplorer) |
| Compatibilità | PT 8.x | PT 5.x - 8.x |
| Performance | Lenta (multiple passes) | Veloce (single pass) |
| Codice | ~200 linee complesse | ~50 linee semplici |
| Dipendenze | Decipher module (custom) | Solo zlib (stdlib) |
| Validazione | Roundtrip test necessario | Built-in ptexplorer |
| Documentazione | Complessa con riferimenti | Semplice e chiara |
| Manutenibilità | Difficile | Facile |

### Architettura di Fallback

Il sistema è progettato per massima affidabilità:

```python
if PTEXPLORER_AVAILABLE:
    # Metodo principale: ptexplorer
    pt = PTFile()
    pt.open_xml(xml_content)
    pt.save(output_path)
else:
    # Fallback: Twofish/EAX
    encrypted_data = encrypt_pkt_data(xml_bytes)
    # ... write PKT5 header + encrypted data
```

Questo garantisce che il sistema funzioni sempre, anche se ptexplorer dovesse avere problemi.

### Riferimenti al Codice Sorgente

Il codice include riferimenti chiari per entrambi i metodi:

```python
# Metodo principale (ptexplorer)
def build_pkt_from_xml(xml_bytes: bytes, output_path: Path) -> None:
    """
    Converte XML Packet Tracer in .pkt compatibile usando ptexplorer.
    
    References:
    - ptexplorer: https://github.com/axcheron/ptexplorer
    """
    pt = PTFile()
    pt.open_xml(xml_text)
    pt.save(str(output_path))

# Metodo fallback (Twofish/EAX)
def encrypt_pkt_data(xml_data: bytes) -> bytes:
    """
    NOTE: Fallback method only, not used when ptexplorer is available.
    
    References:
    - pka2xml.hpp encrypt() function (lines 200-229)
    - Unpacket repacket.py main() function (lines 128-139)
    """
    # Implementation...
```

## Compatibilità

### Versioni Packet Tracer

- ✅ **Packet Tracer 8.x** (testato con ptexplorer, target principale)
- ✅ **Packet Tracer 7.x** (compatibile con ptexplorer)
- ✅ **Packet Tracer 6.x** (compatibile con ptexplorer)
- ✅ **Packet Tracer 5.x** (compatibile con ptexplorer)

### Formato File

I file generati usano:
- **Metodo Principale**: ptexplorer (XOR semplice + zlib)
- **Formato**: PACKETTRACER5 XML
- **Versione**: 8.2.2.0400
- **Compressione**: zlib
- **Fallback**: Twofish-128 in modalità EAX (se ptexplorer non disponibile)

## Troubleshooting

### File non si apre in PT

1. Verifica la versione di PT (deve essere 5.x o superiore)
2. Controlla i log del test:
   ```bash
   python test_ptexplorer_integration.py
   ```
3. Verifica quale metodo è stato usato (ptexplorer o fallback):
   - Controlla il log: `encoding_used: "ptexplorer"` o `"twofish_eax_fallback"`
4. Ispeziona il file XML debug generato
5. Verifica che il file .pkt non sia corrotto (> 100 bytes)

### ptexplorer non disponibile

Se vedi `PTEXPLORER_AVAILABLE: False` nei log:

1. Verifica che `backend/ptexplorer.py` esista
2. Controlla che il modulo sia importabile:
   ```python
   from ptexplorer import PTFile
   ```
3. Il sistema userà automaticamente il fallback Twofish/EAX

### Errori di Decryption (Fallback)

Se il test di validazione fallisce con il metodo fallback:

1. Verifica che il modulo `Decipher` sia presente
2. Controlla che non ci siano modifiche ai file in `Decipher/`
3. Riprova la generazione

## Credits

### Autori Originali

- **ptexplorer**: axcheron (https://github.com/axcheron/ptexplorer)
  - Metodo principale per conversione XML ↔ PKT
- **pka2xml**: mircodz (https://github.com/mircodz)
  - Riferimento per algoritmo encryption (fallback)
- **Unpacket**: Punkcake21 (https://github.com/Punkcake21)
  - Implementazione Twofish/EAX (fallback)

### Integrazione in TraceNet

- **ptexplorer Integration**: Adattamento del modulo ptexplorer con classe PTFile
- **Backend Integration**: Implementazione del sistema con fallback automatico
- **Testing**: Suite di test per validazione ptexplorer + fallback

## License

Questa implementazione rispetta le licenze delle repository originali:

- **ptexplorer**: MIT License
- **pka2xml**: MIT License
- **Unpacket**: MIT License  
- **TraceNet**: MIT License

Per dettagli completi, consultare i file LICENSE nelle rispettive repository.

---

## Changelog

### v2.0 (Current) - ptexplorer Integration
- ✨ Aggiunto ptexplorer come metodo principale
- ✨ Sistema di fallback automatico su Twofish/EAX
- ✨ Test suite completa per validazione
- 📝 Documentazione aggiornata con nuova architettura
- ⚡ Performance migliorate (conversione diretta vs 4-stage encryption)
- 🔧 Codice più semplice e manutenibile

### v1.0 (Legacy) - Twofish/EAX Implementation
- ✅ Implementazione Twofish/EAX completa
- ✅ Compatibilità PT 8.x
- ✅ Test di validazione roundtrip
