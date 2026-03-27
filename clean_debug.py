f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', encoding='utf-8')
lines = f.readlines()
f.close()
clean = [l for l in lines if 'DHCP BEFORE' not in l and 'DHCP AFTER' not in l and 'enabled_el' not in l and 'DEBUG write_dhcp' not in l]
open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', 'w', encoding='utf-8').writelines(clean)
print('Righe dopo pulizia:', len(clean))
