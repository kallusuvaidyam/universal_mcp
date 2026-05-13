# Universal Dev MCP — Setup Guide

## Kya Hai Ye?
Claude AI ko aapke computer ke project se directly connect karne ka tool.
Claude aapki files padh sakta hai, commands chala sakta hai, git use kar sakta hai — sab kuch aapke project mein.

---

## Pehli Baar Setup (Sirf Ek Baar)

### Step 1: Code Download Karo
```bash
git clone https://github.com/YOUR_USERNAME/universal-mcp
cd universal-mcp
```

### Step 2: Setup Wizard Chalao
```bash
python setup_wizard.py
```
Wizard aapko sab guide karega:
- Dependencies install karega
- Cloudflare tunnel setup karega (optional — stable URL ke liye)
- Email setup karega (optional — OTP ke liye)

---

## Roz Use Karna

### Server Start Karo
```bash
# Current folder ke liye:
python main.py start

# Specific project ke liye:
python main.py start --project /path/to/your/project

# Custom port ke liye:
python main.py start --port 5000
```

Output mein aapko URL milega:
```
✅ Local URL  : http://localhost:8080
✅ Remote URL : https://yourname.cfargotunnel.com
```

### Claude.ai Mein Add Karo (Sirf Pehli Baar)
1. Claude.ai → Settings (top right)
2. "Integrations" ya "MCP" section
3. "Add Custom MCP"
4. URL paste karo: `http://localhost:8080` ya Remote URL
5. Save karo

---

## Frappe Plugin (Agar Frappe Use Karte Ho)

Frappe plugin already included hai.

Bas apne Frappe project ki `.mcp-config.json` me `framework: "frappe"` aur required bench/site settings do.

Examples ke liye `plugins/frappe/README.md` padho.

---

## Agar Kuch Problem Ho

**Port already in use:**
```bash
python main.py start --port 9090
```

**Cloudflare tunnel nahi chal raha:**
```bash
cloudflared login
cloudflared tunnel run my-mcp
```

**OTP nahi aaya:**
OTP server terminal mein print hoga — wahan dekho.

---

## Important Files

| File | Kya Hai |
|------|---------|
| `main.py` | Server start karo |
| `setup_wizard.py` | Ek baar setup |
| `plugins/frappe/` | Frappe files yahan |
| `.mcp-config.example.json` | Project config example |
| `~/.universal-dev-mcp/config.json` | Global config |
