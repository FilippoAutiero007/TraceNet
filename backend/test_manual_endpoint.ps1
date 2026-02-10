# Test script for /api/generate-pkt-manual endpoint
# This tests the new structured parameter endpoint

$baseUrl = "http://localhost:8000"

Write-Host "🧪 Testing TraceNet Manual PKT Generation Endpoint" -ForegroundColor Cyan
Write-Host "=" * 60

# Test 1: Health Check
Write-Host "`n📊 Test 1: Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method Get
    Write-Host "✅ Health check passed:" -ForegroundColor Green
    Write-Host ($health | ConvertTo-Json)
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Manual PKT Generation (Structured Parameters)
Write-Host "`n📊 Test 2: Manual PKT Generation (Structured Parameters)" -ForegroundColor Yellow

$manualRequest = @{
    base_network = "192.168.0.0/24"
    subnets = @(
        @{ name = "Admin"; required_hosts = 20 }
        @{ name = "Guest"; required_hosts = 50 }
    )
    devices = @{
        routers = 1
        switches = 2
        pcs = 70
    }
    routing_protocol = "static"
} | ConvertTo-Json -Depth 10

Write-Host "Request body:" -ForegroundColor Gray
Write-Host $manualRequest

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/generate-pkt-manual" `
        -Method Post `
        -ContentType "application/json" `
        -Body $manualRequest
    
    Write-Host "✅ Manual PKT generation successful!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Gray
    Write-Host ($response | ConvertTo-Json -Depth 5)
    
    if ($response.success) {
        Write-Host "`n📥 Download URLs:" -ForegroundColor Cyan
        Write-Host "  PKT: $baseUrl$($response.pkt_download_url)"
        Write-Host "  XML: $baseUrl$($response.xml_download_url)"
    }
} catch {
    Write-Host "❌ Manual PKT generation failed: $_" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode
    exit 1
}

# Test 3: NLP-based PKT Generation (Backward Compatibility)
Write-Host "`n📊 Test 3: NLP-based PKT Generation (Backward Compatibility)" -ForegroundColor Yellow

$nlpRequest = @{
    description = "Create network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing"
} | ConvertTo-Json

Write-Host "Request body:" -ForegroundColor Gray
Write-Host $nlpRequest

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/generate-pkt" `
        -Method Post `
        -ContentType "application/json" `
        -Body $nlpRequest
    
    Write-Host "✅ NLP PKT generation successful!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Gray
    Write-Host ($response | ConvertTo-Json -Depth 5)
} catch {
    Write-Host "⚠️ NLP PKT generation failed (this might be expected if Mistral API key is not configured): $_" -ForegroundColor Yellow
}

Write-Host "`n🎉 Testing complete!" -ForegroundColor Green
