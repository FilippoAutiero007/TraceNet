# Service Bugfix Notes

Ho corretto la gestione dei servizi server nel generatore Packet Tracer per evitare residui del template quando un servizio non deve essere attivo.

## Bug corretti

- DHCP: i server senza servizio `dhcp` non mantengono piu pool attivi o campi come `START_IP` configurati.
- DNS: quando `dns` e spento, i record nel `NAMESERVER-DATABASE` vengono rimossi.
- Mail: quando `smtp`, `pop3` o `email` non sono attivi, dominio e account vengono puliti e il servizio viene disabilitato.
- FTP: quando `ftp` e spento, utenti e account manager vengono svuotati.

## Test aggiunti

Ho aggiunto `backend/tests/test_server_service_cleanup.py` con test di regressione per:

- pulizia DHCP su server senza DHCP
- pulizia record DNS residui
- pulizia account mail residui
- pulizia utenti FTP residui
- riscrittura corretta dei dati quando i servizi vengono poi riattivati

## Nota operativa

Ho lasciato il fix centrato sul codice di generazione XML dei server, cosi i template Packet Tracer esistenti possono continuare a essere usati senza portarsi dietro configurazioni sporche.
