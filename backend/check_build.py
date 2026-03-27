with open("app/services/pkt_generator/server_config.py", "r") as f:
    content = f.read()

# Trova dove viene chiamata build_server_configs e spostala dopo IP assignment
if "build_server_configs(" in content:
    print("build_server_configs già presente")
else:
    print("Funzione mancante - controlla manualmente")
    
print("Controlla dove viene chiamata build_server_configs")
