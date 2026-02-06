# TraceNet - Quick Start Guide

## 🚀 Start the Application (Development Mode)

### Terminal 1 - Backend Server
```bash
cd backend
python3 -m pip install fastapi uvicorn mistralai python-dotenv
python server.py
```
Backend will run on: **http://localhost:8001**

### Terminal 2 - Frontend Server
```bash
cd nettrace
npm install
npm run dev
```
Frontend will run on: **http://localhost:5173**

---

## 📝 Quick Test

### 1. Open the Application
Navigate to: **http://localhost:5173**

### 2. Go to Generator
Click on the **"Try Generator"** button in the navigation bar

### 3. Select a Template
Click on one of the predefined templates:
- Small Office Network
- Corporate Campus
- Data Center
- School Network

### 4. Generate Network
Click **"Generate Network"** button and wait 5-10 seconds

### 5. Download .pkt File
Click **"Download .pkt File"** button
Open the file with Cisco Packet Tracer 8.x or higher

---

## ⚙️ Configuration

### Backend (.env required)
Create `backend/.env` with:
```bash
MISTRAL_API_KEY=your_mistral_api_key_here
OUTPUT_DIR=/tmp/tracenet
ENVIRONMENT=development
```

**Get Mistral API Key**: https://console.mistral.ai/

### Frontend (.env optional)
The frontend uses `nettrace/.env` with default values:
```bash
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

---

## 🧪 API Test with curl

Test the backend API directly:

```bash
# Health check
curl http://localhost:8001/api/health

# Generate network
curl -X POST http://localhost:8001/api/generate-pkt \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create network with 2 VLANs: Admin (20 hosts) and Guest (50 hosts) using static routing"
  }'

# Download file (replace FILENAME with actual filename from response)
curl -O http://localhost:8001/api/download/FILENAME.pkt
```

---

## 🐛 Troubleshooting

### Backend doesn't start
**Error**: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**:
```bash
cd backend
pip install fastapi uvicorn mistralai python-dotenv
```

### Frontend shows connection error
**Error**: "Cannot connect to server"
**Solution**:
1. Make sure backend is running on port 8001
2. Check: `curl http://localhost:8001/api/health`
3. If backend uses different port, update `nettrace/.env`

### Port already in use
**Error**: "Port 8001 already in use"
**Solution**:
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or change port in backend/server.py (line 18)
```

---

## 📦 Production Build

### Build Frontend
```bash
cd nettrace
npm run build
```
Output will be in `nettrace/dist/`

### Run Backend in Production
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 📚 Documentation

- **API Docs (Swagger)**: http://localhost:8001/docs
- **API Docs (ReDoc)**: http://localhost:8001/redoc
- **GitHub Repository**: https://github.com/FilippoAutiero007/TraceNet

---

## ✅ Feature Checklist (P1 - All Complete!)

- [x] CSS white sidebars fixed
- [x] React Router DOM installed and configured
- [x] Landing page wrapper created
- [x] Generator page with two-column layout
- [x] NetworkInput component with 4 templates
- [x] DownloadResult component with subnet table
- [x] API integration with error handling
- [x] Navigation with "Try Generator" button
- [x] Environment variables configured
- [x] Complete README documentation

---

## 🎯 Next Steps (P2 Features)

- [ ] Add user authentication with Clerk
- [ ] Implement network topology visualization
- [ ] Add configuration history
- [ ] Support for more routing protocols (BGP, ISIS)
- [ ] Advanced ACL and NAT configurations
- [ ] Export to EVE-NG and GNS3 formats
- [ ] Community template marketplace

---

**Happy Networking! 🌐**
