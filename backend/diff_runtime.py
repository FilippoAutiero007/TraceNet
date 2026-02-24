import xml.etree.ElementTree as ET
import re

def extract_all(file):
    try:
        r = ET.parse(file).getroot()
        all_text = ET.tostring(r, encoding='unicode')
        
        # MAC patterns comuni in PT XML
        macs_colon = re.findall(r'\b[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}\b', all_text)
        macs_dash = re.findall(r'\b[0-9A-Fa-f]{2}(-[0-9A-Fa-f]{2}){5}\b', all_text)
        macs_no_sep = re.findall(r'\b[0-9A-Fa-f]{12}\b', all_text)
        
        serials = [e.text for e in r.iter() if e.text and ('PT' in e.text or e.text.startswith('PT'))]
        saverefs = [e.text for e in r.iter() if e.text and 'save-ref-id' in str(e.tag or '')]
        
        print(f"{file}:")
        print(f"  MAC colon: {len(macs_colon)} {macs_colon[:3]}")
        print(f"  MAC dash: {len(macs_dash)} {macs_dash[:3]}")
        print(f"  MAC hex12: {len(macs_no_sep)} {macs_no_sep[:3]}")
        print(f"  Serials: {len(serials)} {serials[:3]}")
        print(f"  SaveRefs: {len(saverefs)} {saverefs[:3]}")
        print()
        
    except Exception as e:
        print(f"{file}: ERRORE {e}")

extract_all('testok.xml')
extract_all('kotest.xml')
