f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

old = '                "name": f"{d.get(\"name\", \"server\")}_pool",'
new = '                "name": "serverPool",'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
