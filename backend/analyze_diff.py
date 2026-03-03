import xml.etree.ElementTree as ET
from pathlib import Path

orig = ET.parse("debug_orig_router8.xml").getroot()
gen = ET.parse("debug_gen_router8.xml").getroot()

def count_elements(node, path=""):
    counts = {}
    for child in node:
        tag = child.tag
        full_path = f"{path}/{tag}" if path else tag
        counts[full_path] = counts.get(full_path, 0) + 1
        child_counts = count_elements(child, full_path)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v
    return counts

orig_counts = count_elements(orig)
gen_counts = count_elements(gen)

print("=== ELEMENTI MANCANTI NEL FILE GENERATO ===\n")
for path in sorted(orig_counts.keys()):
    orig_count = orig_counts[path]
    gen_count = gen_counts.get(path, 0)
    if gen_count < orig_count:
        print(f"❌ {path}: {orig_count} → {gen_count} (mancano {orig_count - gen_count})")

print("\n=== ELEMENTI AGGIUNTI NEL FILE GENERATO ===\n")
for path in sorted(gen_counts.keys()):
    gen_count = gen_counts[path]
    orig_count = orig_counts.get(path, 0)
    if gen_count > orig_count:
        print(f"➕ {path}: {orig_count} → {gen_count} (aggiunti {gen_count - orig_count})")
