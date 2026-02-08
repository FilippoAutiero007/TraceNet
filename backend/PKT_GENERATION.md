# TraceNet - Packet Tracer File Generation

## Nuova Implementazione Crittografica

Questa implementazione utilizza le seguenti repository come riferimento tecnico per garantire la compatibilità con Cisco Packet Tracer 8.x:

### Repository di Riferimento

1. **pka2xml** (mircodz)
   - Repository: https://github.com/mircodz/pka2xml
   - Utilizzo: Analisi della struttura XML e dell'algoritmo di crittografia
   - Contributo: Comprensione del formato PT 8.x e del pipeline di encryption

2. **Unpacket** (Punkcake21)
   - Repository: https://github.com/Punkcake21/Unpacket
   - Utilizzo: Implementazione pura Python di Twofish/EAX
   - Contributo: Libreria crittografica senza dipendenze esterne

## Architettura

### Moduli Principali

```
backend/app/services/
├── pkt_crypto.py          # Crittografia Twofish/EAX (da Unpacket)
├── pkt_xml_builder.py     # Costruzione XML PT 8.x (ispirato a pka2xml)
├── pkt_file_generator.py  # Orchestrazione generazione file
└── ...

backend/Decipher/          # Libreria crittografica da Unpacket
├── twofish.py            # Implementazione Twofish-128
├── eax.py                # Modalità EAX (AEAD)
├── cmac.py               # CMAC per autenticazione
└── ctr.py                # Counter mode
```

### Pipeline di Encryption

Il processo di crittografia segue esattamente l'algoritmo implementato da Cisco Packet Tracer, come documentato in **pka2xml.hpp**:

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

### Test di Generazione

```bash
cd backend
python test_pkt_generation_new.py
```

Questo test:
1. ✅ Costruisce una rete di esempio con 2 subnet
2. ✅ Genera il file XML con struttura PT 8.x
3. ✅ Cripta il file usando Twofish/EAX
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

## Vantaggi della Nuova Implementazione

### Rispetto alla Vecchia Implementazione

| Aspetto | Vecchia | Nuova |
|---------|---------|-------|
| Crittografia | XOR semplice | Twofish/EAX (standard PT) |
| Compatibilità | PT 6.x | PT 8.x |
| Validazione | Nessuna | Roundtrip test |
| Documentazione | Minima | Completa con riferimenti |
| Dipendenze | Esterne (subprocess) | Pure Python |

### Riferimenti al Codice Sorgente

Ogni funzione critica include riferimenti precisi:

```python
def encrypt_pkt_data(xml_data: bytes) -> bytes:
    """
    References:
    - pka2xml.hpp encrypt() function (lines 200-229)
    - Unpacket repacket.py main() function (lines 128-139)
    """
    # Implementation...
```

## Compatibilità

### Versioni Packet Tracer

- ✅ **Packet Tracer 8.x** (testato, target principale)
- ✅ **Packet Tracer 7.x** (dovrebbe funzionare)
- ❓ **Packet Tracer 6.x** (non testato, probabile compatibilità)

### Formato File

I file generati usano:
- **Formato**: PACKETTRACER5 XML
- **Versione**: 8.2.2.0400
- **Crittografia**: Twofish-128 in modalità EAX
- **Compressione**: zlib (Qt style)

## Troubleshooting

### File non si apre in PT

1. Verifica la versione di PT (deve essere 8.x o superiore)
2. Controlla i log del test:
   ```bash
   python test_pkt_generation_new.py
   ```
3. Ispeziona il file XML debug generato
4. Verifica che il file .pkt non sia corrotto (> 500 bytes)

### Errori di Decryption

Se il test di validazione fallisce:

1. Verifica che il modulo `Decipher` sia presente
2. Controlla che non ci siano modifiche ai file in `Decipher/`
3. Riprova la generazione

## Credits

### Autori Originali

- **pka2xml**: mircodz (https://github.com/mircodz)
- **Unpacket**: Punkcake21 (https://github.com/Punkcake21)

### Integrazione in TraceNet

- **Backend Integration**: Implementazione dell'integrazione con TraceNet
- **Testing**: Validazione e test suite

## License

Questa implementazione rispetta le licenze delle repository originali:

- **pka2xml**: MIT License
- **Unpacket**: MIT License  
- **TraceNet**: MIT License

Per dettagli completi, consultare i file LICENSE nelle rispettive repository.
