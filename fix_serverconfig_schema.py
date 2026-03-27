f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\models\schemas.py', encoding='utf-8')
content = f.read()
f.close()

old = '    auto_dns_records: bool = Field(default=False)'
new = '    auto_dns_records: bool = Field(default=False)\n    dhcp_pools: Optional[list] = Field(default=None, description="Custom DHCP pool names for this server")'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\models\schemas.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
