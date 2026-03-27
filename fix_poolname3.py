f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

# Fix pool aggiuntivi - nome basato sulla rete
old = '                    "name": f"{d.get(\"name\", \"server\")}_{seg_net.replace(\".\", \"_\")}_pool",'
new = '                    "name": f"rete{seg_net.split(\"/\")[0] if \"/\" in seg_net else seg_net}",'

if old in content:
    content = content.replace(old, new)
    print("Fix pool aggiuntivi: OK")
else:
    print("Fix pool aggiuntivi: ERRORE")

open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
