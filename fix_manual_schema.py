f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\models\manual_schemas.py', encoding='utf-8')
content = f.read()
f.close()

# Aggiungi import ServerConfig se non presente
if 'ServerConfig' not in content:
    content = content.replace(
        'from app.models.schemas import RoutingProtocol, DeviceConfig, SubnetRequest, TopologyConfig',
        'from app.models.schemas import RoutingProtocol, DeviceConfig, SubnetRequest, TopologyConfig, ServerConfig, PcConfig'
    )

# Aggiungi i campi mancanti dopo server_services
old = '    server_services: Optional[List[str]] = Field(default=None, description="Services to enable on server (dns, http, dhcp, ftp...)")'
new = '''    server_services: Optional[List[str]] = Field(default=None, description="Services to enable on server (dns, http, dhcp, ftp...)")
    dhcp_from_router: bool = Field(default=False, description="Enable IOS DHCP pools on router interfaces")
    servers_config: Optional[List[ServerConfig]] = Field(default=None, description="Per-server configuration")
    pcs_config: Optional[List[PcConfig]] = Field(default=None, description="Per-PC configuration")'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\models\manual_schemas.py', 'w', encoding='utf-8').write(content)
    print('OK - campi aggiunti')
else:
    print('ERRORE - riga non trovata')
    print('Contenuto:', content[:500])
