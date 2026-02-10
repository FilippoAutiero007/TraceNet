# Test the generated PKT file directly
Write-Host "🧪 Testing Generated PKT File" -ForegroundColor Cyan
Write-Host "=" * 60

$testOutputDir = "test_output"
$pktFiles = Get-ChildItem -Path $testOutputDir -Filter "*.pkt" | Sort-Object LastWriteTime -Descending

if ($pktFiles.Count -eq 0) {
    Write-Host "❌ No PKT files found in $testOutputDir" -ForegroundColor Red
    Write-Host "Run test_template_generation.py first" -ForegroundColor Yellow
    exit 1
}

$latestPkt = $pktFiles[0]
Write-Host "`n📄 Latest PKT file: $($latestPkt.Name)" -ForegroundColor Green
Write-Host "   Size: $($latestPkt.Length) bytes"
Write-Host "   Created: $($latestPkt.LastWriteTime)"

# Check if file size indicates proper encryption
if ($latestPkt.Length -gt 10000) {
    Write-Host "`n✅ File size looks good (encrypted PKT)" -ForegroundColor Green
}
else {
    Write-Host "`n⚠️  File size seems small - may not be properly encrypted" -ForegroundColor Yellow
}

# Try to open in Packet Tracer
Write-Host "`n🚀 Attempting to open in Packet Tracer..." -ForegroundColor Cyan
Write-Host "   File: $($latestPkt.FullName)"

$packetTracerPath = "C:\Program Files\Cisco Packet Tracer 8.2.2\bin\PacketTracer.exe"

if (Test-Path $packetTracerPath) {
    Write-Host "`n✅ Packet Tracer found!" -ForegroundColor Green
    Write-Host "   Opening file..." -ForegroundColor Cyan
    
    Start-Process -FilePath $packetTracerPath -ArgumentList "`"$($latestPkt.FullName)`""
    
    Write-Host "`n📊 Please check Packet Tracer:" -ForegroundColor Yellow
    Write-Host "   1. Does the file open without errors?" 
    Write-Host "   2. Are the devices visible?"
    Write-Host "   3. Are the IPs configured correctly?"
    
}
else {
    Write-Host "`n⚠️  Packet Tracer not found at: $packetTracerPath" -ForegroundColor Yellow
    Write-Host "   Please open the file manually:" -ForegroundColor Cyan
    Write-Host "   $($latestPkt.FullName)"
}

Write-Host "`n" -NoNewline
Read-Host "Press Enter to continue"
