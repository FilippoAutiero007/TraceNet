# NetTrace MCP Server

Generatore di reti Cisco Packet Tracer (.pkt) da linguaggio naturale.

## Funzionalità
- Parsing di descrizioni NLP per estrarre topologia e requisiti.
- Calcolo automatico VLSM per ottimizzazione indirizzi IP.
- Generazione di configurazioni IOS complete (Hostname, Interfacce, RIP/OSPF).
- Esportazione in formato `.pkt` (XML compresso con gzip) compatibile con Packet Tracer 8.x.

## Installazione
1. Assicurati di avere Python 3.10+ installato.
2. Installa le dipendenze:
   ```bash
   pip install mcp openai pydantic
   ```
3. Configura la tua chiave API OpenAI nell'ambiente.

## Utilizzo con Claude Desktop
Aggiungi quanto segue al tuo file `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nettrace": {
      "command": "python",
      "args": ["-m", "nettrace.server"],
      "env": {
        "OPENAI_API_KEY": "tua_chiave_api"
      }
    }
  }
}
```

## Esempio di Chiamata
"Crea una rete con 2 VLAN: Vendite (50 host) e IT (20 host). Usa OSPF come protocollo di routing."
