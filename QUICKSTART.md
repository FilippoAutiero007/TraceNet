# SOLUZIONE RAPIDA - Copia tutto questo blocco
$body = '{"base_network":"192.168.0.0/24","routers":1,"switches":2,"pcs":6,"routing_protocol":"static","subnets":[{"name":"Admin","required_hosts":20},{"name":"Guest","required_hosts":50}]}'
$response = Invoke-RestMethod -Method Post -Uri "https://tracenet-api.onrender.com/api/generate-pkt" -ContentType "application/json" -Body $body
if ($response.success) {
    $url = "https://tracenet-api.onrender.com$($response.pkt_download_url)"
    Invoke-WebRequest -Uri $url -OutFile "network.pkt"
    Write-Host "✅ File scaricato: network.pkt" -ForegroundColor Green
    explorer.exe (Get-Location).Path  # Apre la cartella
} else {
    Write-Host "❌ Errore: $($response.error)" -ForegroundColor Red
}
