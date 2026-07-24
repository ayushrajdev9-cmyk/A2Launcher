#!/usr/bin/env python3
"""
A2Launcher - Minecraft Launcher by Ayush Rajdev & Anzar Iqbal
Web-based UI - Beautiful modern design, runs in your browser!
"""

import os, sys, json, time, subprocess, platform, threading, webbrowser, requests
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

VERSION = "3.0.0"
AUTHORS = "Ayush Rajdev & Anzar Iqbal"
PORT = 25565

BASE_DIR = Path.home() / ".a2launcher"
VERSIONS_DIR = BASE_DIR / "versions"
MINECRAFT_DIR = Path.home() / "AppData" / "Roaming" / ".minecraft"
CONFIG_FILE = BASE_DIR / "config.json"
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

for d in [BASE_DIR, VERSIONS_DIR, MINECRAFT_DIR/"mods"]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Config ────────────────────────────────────────────────
class Config:
    def __init__(self):
        self.data = CONFIG_FILE.exists() and json.load(open(CONFIG_FILE)) or {"username":"Player","ram":2048,"width":854,"height":480,"java":"","version":"latest_release","server":""}
        if not CONFIG_FILE.exists(): self.save()
    def save(self): json.dump(self.data, open(CONFIG_FILE,"w"), indent=2)
    def g(self,k,d=None): return self.data.get(k,d)
    def s(self,k,v): self.data[k]=v; self.save()

config = Config()

# ─── Version Manager ──────────────────────────────────────
class VM:
    def __init__(self):
        self.manifest = None; self.versions = []
    def fetch(self):
        try:
            r = requests.get(MANIFEST_URL, timeout=15)
            if r.status_code==200: self.manifest=r.json(); self.versions=self.manifest.get("versions",[]); return True
        except: pass
        return False
    def get_list(self):
        if not self.manifest: self.fetch()
        return [v for v in self.versions if v["type"] in ["release","snapshot"]]
    def get_json(self, vid):
        p = VERSIONS_DIR/vid/f"{vid}.json"
        if p.exists(): return json.load(open(p))
        url = next((v["url"] for v in self.versions if v["id"]==vid),None)
        if not url: return None
        try:
            r = requests.get(url,timeout=15)
            if r.status_code==200: (VERSIONS_DIR/vid).mkdir(exist_ok=True); json.dump(r.json(),open(p,"w"),indent=2); return r.json()
        except: pass
        return None
    def get_installed(self):
        return [d.name for d in VERSIONS_DIR.iterdir() if d.is_dir() and (d/f"{d.name}.jar").exists()]

vm = VM()

# ─── Launch Logic ─────────────────────────────────────────
launch_status = {"status": "idle", "message": "Ready to play!"}

def find_java(vid):
    cfg = config.g("java","")
    if cfg and os.path.exists(cfg): return cfg
    try:
        parts = vid.split(".")
        if vid.startswith("1.") and len(parts)>1:
            sub = int(parts[1]); maj = 17 if sub>=18 else (11 if sub>=16 else 8)
        else: maj = 17
    except: maj = 17
    paths = [os.environ.get("JAVA_HOME","")]
    for pf in [os.environ.get("ProgramFiles","C:\\Program Files"), os.environ.get("ProgramFiles(x86)","C:\\Program Files (x86)")]:
        if os.path.exists(pf):
            for d in os.listdir(pf):
                if any(x in d.lower() for x in ["java","jdk","jre","adopt","semeru"]):
                    j = os.path.join(pf,d,"bin","javaw.exe")
                    if os.path.exists(j): paths.append(j)
    paths += [r"C:\Program Files\Java\jdk-17\bin\javaw.exe",r"C:\Program Files\Java\jdk-21\bin\javaw.exe"]
    for p in paths:
        if p and os.path.exists(p): config.s("java",p); return p
    try: subprocess.run(["java","-version"],capture_output=True,timeout=5); config.s("java","java"); return "java"
    except: return None

def launch_minecraft(data):
    global launch_status
    name = data.get("username","Player")
    vid = data.get("version","latest_release")
    ram_mb = int(data.get("ram",2048))
    w = int(data.get("width",854))
    h = int(data.get("height",480))
    
    if vid=="latest_release":
        for v in vm.get_list():
            if v["type"]=="release": vid=v["id"]; break
    elif vid=="latest_snapshot":
        for v in vm.get_list():
            if v["type"]=="snapshot": vid=v["id"]; break
    
    launch_status = {"status":"launching","message":f"Launching Minecraft {vid}..."}
    
    def thread():
        global launch_status
        try:
            vj = vm.get_json(vid)
            if not vj: launch_status={"status":"error","message":f"Version {vid} not found"}; return
            java = find_java(vid)
            if not java: launch_status={"status":"error","message":"Java not found! Install from adoptium.net"}; return
            
            cp = []
            cj = VERSIONS_DIR/vid/f"{vid}.jar"
            if cj.exists(): cp.append(str(cj))
            lib_dir = BASE_DIR/"libraries"
            for lib in vj.get("libraries",[]):
                art = lib.get("downloads",{}).get("artifact",{})
                lp = lib_dir/art.get("path","")
                if lp.exists(): cp.append(str(lp))
            
            sep = ";" if platform.system()=="Windows" else ":"
            natives = str(BASE_DIR/"natives"/vid)
            os.makedirs(natives,exist_ok=True)
            main = vj.get("mainClass","net.minecraft.client.main.Main")
            
            args = [f"-Xmx{ram_mb}M",f"-Xms{ram_mb//2}M","-Djava.library.path="+natives,"-cp",sep.join(cp),
                    main,"--username",name,"--version",vid,"--gameDir",str(MINECRAFT_DIR),
                    "--assetsDir",str(BASE_DIR/"assets"),"--assetIndex",vj.get("assetIndex",{}).get("id","legacy"),
                    "--uuid","00000000-0000-0000-0000-000000000000","--accessToken","0",
                    "--userType","mojang","--versionType",vj.get("type","release"),
                    "--width",str(w),"--height",str(h)]
            
            # Auto-connect to server if specified
            server_ip = data.get("server","").strip()
            if server_ip:
                server_parts = server_ip.split(":")
                args.extend(["--server", server_parts[0]])
                args.extend(["--port", server_parts[1] if len(server_parts) > 1 else "25565"])
            
            launch_status = {"status":"running","message":f"▶ Minecraft {vid} is running! Close the game when done."}
            subprocess.Popen([java]+args,cwd=str(MINECRAFT_DIR),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).wait()
            launch_status = {"status":"idle","message":"✅ Game closed. Ready to play again."}
        except Exception as e:
            launch_status = {"status":"error","message":f"Error: {str(e)}"}
    
    threading.Thread(target=thread,daemon=True).start()
    return {"status":"launching"}

# ─── THE UI ────────────────────────────────────────────────
HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A2Launcher - Minecraft Launcher</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
body{font-family:'Inter',sans-serif;background:#0a0c10;color:#e8edf2;overflow:hidden;height:100vh;user-select:none}

/* ─── Scrollbar ─── */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#0a0c10}
::-webkit-scrollbar-thumb{background:#1e293b;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#334155}

/* ─── Layout ─── */
.app{display:flex;height:100vh}
.sidebar{width:220px;background:#0f1219;border-right:1px solid #1a1f2e;display:flex;flex-direction:column;flex-shrink:0}
.sidebar-logo{padding:24px 20px 20px;border-bottom:1px solid #1a1f2e}
.sidebar-logo h1{font-size:20px;font-weight:800;background:linear-gradient(135deg,#00d4ff,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px}
.sidebar-logo span{font-size:11px;color:#64748b;font-weight:400;margin-top:2px;display:block;-webkit-text-fill-color:#64748b}
.sidebar-nav{padding:12px 8px;flex:1}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:8px;color:#64748b;font-size:13px;font-weight:500;cursor:pointer;transition:all 0.2s;margin-bottom:2px}
.nav-item:hover{background:#1a1f2e;color:#e8edf2}
.nav-item.active{background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(124,58,237,0.12));color:#00d4ff;border:1px solid rgba(0,212,255,0.15)}
.nav-item .icon{font-size:16px;width:24px;text-align:center}
.sidebar-footer{padding:16px;border-top:1px solid #1a1f2e;font-size:11px;color:#334155;text-align:center}

/* ─── Main Content ─── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:16px 30px;background:#0d1017;border-bottom:1px solid #1a1f2e}
.topbar-left{display:flex;align-items:center;gap:12px}
.topbar-left h2{font-size:16px;font-weight:600;color:#e8edf2}
.status-dot{width:8px;height:8px;border-radius:50%;background:#06d6a0;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.topbar-right{display:flex;align-items:center;gap:10px}
.topbar-right span{font-size:12px;color:#64748b}

.content{flex:1;padding:30px;overflow-y:auto;display:flex;gap:25px}

/* ─── Left Panel ─── */
.panel-left{flex:1;max-width:560px}
.panel-right{width:300px;flex-shrink:0}

/* ─── Cards ─── */
.card{background:#10141e;border:1px solid #1a1f2e;border-radius:12px;padding:22px;margin-bottom:16px;transition:border-color 0.3s}
.card:hover{border-color:#252d3e}
.card-title{font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px}

/* ─── Inputs ─── */
.input-group{display:flex;flex-direction:column;gap:4px}
.input-group label{font-size:11px;font-weight:500;color:#64748b;text-transform:uppercase;letter-spacing:0.5px}
.input-group input,.input-group select{background:#080b12;border:1px solid #1a1f2e;border-radius:8px;padding:10px 14px;font-size:14px;color:#e8edf2;outline:none;transition:all 0.2s;font-family:'Inter',sans-serif}
.input-group input:focus,.input-group select:focus{border-color:#00d4ff;box-shadow:0 0 0 3px rgba(0,212,255,0.1)}
.input-group select{appearance:none;cursor:pointer;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2364748b' d='M6 8L1 3h10z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center}

/* ─── Username Row ─── */
.username-row{display:flex;gap:12px}
.username-row .input-group{flex:1}

/* ─── Slider ─── */
.slider-group{display:flex;flex-direction:column;gap:6px}
.slider-header{display:flex;justify-content:space-between;align-items:center}
.slider-header label{font-size:11px;font-weight:500;color:#64748b;text-transform:uppercase;letter-spacing:0.5px}
.slider-value{font-size:18px;font-weight:700;color:#00d4ff}
input[type="range"]{-webkit-appearance:none;width:100%;height:4px;background:#1a1f2e;border-radius:2px;outline:none;transition:background 0.2s}
input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:linear-gradient(135deg,#00d4ff,#7c3aed);cursor:pointer;border:2px solid #0a0c10;box-shadow:0 0 10px rgba(0,212,255,0.3)}
input[type="range"]::-webkit-slider-thumb:hover{transform:scale(1.1)}
input[type="range"]::-moz-range-thumb{width:18px;height:18px;border-radius:50%;background:linear-gradient(135deg,#00d4ff,#7c3aed);cursor:pointer;border:2px solid #0a0c10}

/* ─── Resolution ─── */
.res-row{display:flex;gap:10px;align-items:end}
.res-row .input-group{flex:1}
.res-row .sep{font-size:20px;color:#475569;padding-bottom:10px;font-weight:300}

/* ─── Play Button ─── */
.play-btn{width:100%;padding:16px;border:none;border-radius:12px;font-size:18px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,#00d4ff,#7c3aed);color:#fff;letter-spacing:1px;transition:all 0.3s;font-family:'Inter',sans-serif;position:relative;overflow:hidden}
.play-btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,212,255,0.3)}
.play-btn:active{transform:translateY(0)}
.play-btn:disabled{opacity:0.5;cursor:not-allowed;transform:none;box-shadow:none}
.play-btn .shine{position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent);animation:shine 3s infinite}
@keyframes shine{to{left:100%}}

/* ─── Right Panel ─── */
.panel-right .card{padding:16px}
.quick-btn{display:block;width:100%;padding:10px;margin-bottom:6px;border:none;border-radius:8px;background:#080b12;color:#94a3b8;font-size:12px;font-weight:500;cursor:pointer;transition:all 0.2s;text-align:left;font-family:'Inter',sans-serif;border:1px solid #1a1f2e}
.quick-btn:hover{background:#1a1f2e;color:#e8edf2;border-color:#252d3e}
.quick-btn .emoji{margin-right:8px}

/* ─── Status Bar ─── */
.statusbar{display:flex;align-items:center;justify-content:space-between;padding:10px 30px;background:#0d1017;border-top:1px solid #1a1f2e;font-size:12px;color:#64748b}
.statusbar .status-msg{display:flex;align-items:center;gap:8px}
.statusbar .credits{color:#334155;font-size:11px}

/* ─── Loading ─── */
.loading{display:flex;align-items:center;justify-content:center;padding:40px;color:#475569;gap:10px}
.spinner{width:20px;height:20px;border:2px solid #1a1f2e;border-top-color:#00d4ff;border-radius:50%;animation:spin 0.8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ─── Animations ─── */
.fade-in{animation:fadeIn 0.4s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

@media(max-width:900px){
  .content{flex-direction:column}
  .panel-right{width:100%}
  .sidebar{width:60px}
  .sidebar-logo h1{font-size:14px}
  .sidebar-logo span,.nav-item span{display:none}
  .nav-item{justify-content:center;padding:10px}
}
</style>
</head>
<body>
<div class="app">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-logo">
      <h1>⛏ A2</h1>
      <span>by Ayush & Anzar</span>
    </div>
    <div class="sidebar-nav">
      <div class="nav-item active"><span class="icon">🏠</span><span>Dashboard</span></div>
      <div class="nav-item" onclick="window.open('https://files.minecraftforge.net/')"><span class="icon">📦</span><span>Forge</span></div>
      <div class="nav-item" onclick="window.open('https://fabricmc.net/use/')"><span class="icon">🧵</span><span>Fabric</span></div>
      <div class="nav-item" onclick="window.open('https://optifine.net/downloads')"><span class="icon">✨</span><span>OptiFine</span></div>
    </div>
    <div class="sidebar-footer">v3.0.0</div>
  </div>

  <!-- Main -->
  <div class="main">
    <div class="topbar">
      <div class="topbar-left">
        <div class="status-dot" id="statusDot"></div>
        <h2 id="statusTitle">Ready</h2>
      </div>
      <div class="topbar-right">
        <span>⭐ <a href="https://github.com/ayushrajdev9-cmyk/A2Launcher" target="_blank" style="color:#64748b;text-decoration:none">GitHub</a></span>
      </div>
    </div>

    <div class="content">
      <div class="panel-left fade-in">
        <!-- Username + Server -->
        <div class="card">
          <div class="card-title">Player & Server</div>
          <div class="username-row">
            <div class="input-group">
              <label>Username</label>
              <input type="text" id="username" value="Player" placeholder="Enter username">
            </div>
            <div class="input-group">
              <label>Server IP (optional)</label>
              <input type="text" id="server" placeholder="e.g. mc.hypixel.net">
            </div>
          </div>
        </div>

        <!-- Version + Play -->
        <div class="card">
          <div class="card-title">Launch Options</div>
          <div class="input-group" style="margin-bottom:14px">
            <label>Minecraft Version</label>
            <select id="version"><option value="">Loading versions...</option></select>
          </div>

          <div class="slider-group" style="margin-bottom:14px">
            <div class="slider-header">
              <label>RAM Allocation</label>
              <span class="slider-value" id="ramLabel">2048 MB</span>
            </div>
            <input type="range" id="ramSlider" min="512" max="16384" value="2048" step="128">
          </div>

          <div class="res-row" style="margin-bottom:16px">
            <div class="input-group">
              <label>Width</label>
              <input type="number" id="width" value="854" min="400" max="3840">
            </div>
            <div class="sep">×</div>
            <div class="input-group">
              <label>Height</label>
              <input type="number" id="height" value="480" min="300" max="2160">
            </div>
          </div>

          <button class="play-btn" id="playBtn" onclick="launchGame()">
            <span class="shine"></span>
            ▶ PLAY
          </button>
        </div>
      </div>

      <div class="panel-right fade-in">
        <!-- Quick Actions -->
        <div class="card">
          <div class="card-title">Quick Actions</div>
          <button class="quick-btn" onclick="window.open('https://files.minecraftforge.net/')"><span class="emoji">📦</span>Install Forge</button>
          <button class="quick-btn" onclick="window.open('https://fabricmc.net/use/')"><span class="emoji">🧵</span>Install Fabric</button>
          <button class="quick-btn" onclick="window.open('https://optifine.net/downloads')"><span class="emoji">✨</span>Install OptiFine</button>
          <button class="quick-btn" onclick="fetch('/api/open-mods')"><span class="emoji">📂</span>Open Mods Folder</button>
          <button class="quick-btn" onclick="fetch('/api/open-minecraft')"><span class="emoji">📂</span>Open .minecraft</button>
          <button class="quick-btn" onclick="loadVersions()"><span class="emoji">🔄</span>Refresh Versions</button>
        </div>

        <!-- Server Browser -->
        <div class="card">
          <div class="card-title">🌍 Server Browser - Click to Join</div>
          <div id="serverList" style="max-height:220px;overflow-y:auto">
            <div class="server-item" onclick="joinServer('mc.hypixel.net')" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;cursor:pointer;transition:all 0.2s;margin-bottom:3px;background:#080b12;border:1px solid #1a1f2e" onmouseover="this.style.borderColor='#00d4ff'" onmouseout="this.style.borderColor='#1a1f2e'">
              <span style="font-size:20px">⚔️</span>
              <div style="flex:1"><strong style="font-size:13px;color:#e8edf2">Hypixel</strong><br><span style="font-size:10px;color:#64748b">mc.hypixel.net • 50k+ players</span></div>
              <span style="color:#06d6a0;font-size:11px;font-weight:600">● ONLINE</span>
            </div>
            <div class="server-item" onclick="joinServer('play.cubecraft.net')" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;cursor:pointer;transition:all 0.2s;margin-bottom:3px;background:#080b12;border:1px solid #1a1f2e" onmouseover="this.style.borderColor='#00d4ff'" onmouseout="this.style.borderColor='#1a1f2e'">
              <span style="font-size:20px">🎯</span>
              <div style="flex:1"><strong style="font-size:13px;color:#e8edf2">CubeCraft</strong><br><span style="font-size:10px;color:#64748b">play.cubecraft.net • 10k+ players</span></div>
              <span style="color:#06d6a0;font-size:11px;font-weight:600">● ONLINE</span>
            </div>
            <div class="server-item" onclick="joinServer('play.hivemc.com')" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;cursor:pointer;transition:all 0.2s;margin-bottom:3px;background:#080b12;border:1px solid #1a1f2e" onmouseover="this.style.borderColor='#00d4ff'" onmouseout="this.style.borderColor='#1a1f2e'">
              <span style="font-size:20px">🐝</span>
              <div style="flex:1"><strong style="font-size:13px;color:#e8edf2">HiveMC</strong><br><span style="font-size:10px;color:#64748b">play.hivemc.com • 5k+ players</span></div>
              <span style="color:#06d6a0;font-size:11px;font-weight:600">● ONLINE</span>
            </div>
            <div class="server-item" onclick="joinServer('play.minemen.club')" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;cursor:pointer;transition:all 0.2s;margin-bottom:3px;background:#080b12;border:1px solid #1a1f2e" onmouseover="this.style.borderColor='#00d4ff'" onmouseout="this.style.borderColor='#1a1f2e'">
              <span style="font-size:20px">🏆</span>
              <div style="flex:1"><strong style="font-size:13px;color:#e8edf2">Minemen Club</strong><br><span style="font-size:10px;color:#64748b">play.minemen.club • 3k+ players</span></div>
              <span style="color:#06d6a0;font-size:11px;font-weight:600">● ONLINE</span>
            </div>
            <div class="server-item" onclick="joinServer('play.pixelmonmc.com')" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:6px;cursor:pointer;transition:all 0.2s;margin-bottom:3px;background:#080b12;border:1px solid #1a1f2e" onmouseover="this.style.borderColor='#00d4ff'" onmouseout="this.style.borderColor='#1a1f2e'">
              <span style="font-size:20px">🔥</span>
              <div style="flex:1"><strong style="font-size:13px;color:#e8edf2">PixelmonMC</strong><br><span style="font-size:10px;color:#64748b">play.pixelmonmc.com • 2k+ players</span></div>
              <span style="color:#06d6a0;font-size:11px;font-weight:600">● ONLINE</span>
            </div>
          </div>
          <div style="margin-top:8px;display:flex;gap:6px">
            <input type="text" id="customServer" placeholder="Enter custom server IP..." style="flex:1;background:#080b12;border:1px solid #1a1f2e;border-radius:6px;padding:8px 10px;font-size:12px;color:#e8edf2;outline:none;font-family:'Inter',sans-serif">
            <button onclick="joinServer(document.getElementById('customServer').value)" style="background:linear-gradient(135deg,#00d4ff,#7c3aed);border:none;border-radius:6px;padding:8px 14px;color:#fff;font-size:12px;font-weight:600;cursor:pointer;font-family:'Inter',sans-serif">Join</button>
          </div>
        </div>

        <!-- Tips -->
        <div class="card">
          <div class="card-title">💡 Tips</div>
          <div style="font-size:12px;color:#64748b;line-height:1.6">
            • Allocate <strong style="color:#00d4ff">2-4GB</strong> for modded MC<br>
            • MC 1.18+ needs <strong style="color:#00d4ff">Java 17</strong><br>
            • Use OptiFine for better FPS<br>
            • Run as admin if launch fails<br>
            • Made with ❤️ by Ayush & Anzar 🇮🇳
          </div>
        </div>

        <!-- Status -->
        <div class="card" id="statusCard">
          <div class="card-title">Status</div>
          <div id="statusMsg" style="font-size:13px;color:#06d6a0">🟢 Ready to play!</div>
        </div>
      </div>
    </div>

    <div class="statusbar">
      <div class="status-msg"><span id="statusSmall">Ready</span></div>
      <div class="credits">A2Launcher by Ayush Rajdev & Anzar Iqbal</div>
    </div>
  </div>
</div>

<script>
// ─── Load Versions ───
async function loadVersions() {
  const sel = document.getElementById('version');
  sel.innerHTML = '<option>Loading...</option>';
  try {
    const r = await fetch('/api/versions');
    const d = await r.json();
    sel.innerHTML = '';
    if(d.success) {
      sel.innerHTML += '<option value="latest_release">Latest Release</option>';
      sel.innerHTML += '<option value="latest_snapshot">Latest Snapshot</option>';
      sel.innerHTML += '<option disabled>──────────</option>';
      d.releases.forEach(v => { sel.innerHTML += `<option value="${v}">${v}</option>` });
      sel.innerHTML += '<option disabled>────────── SNAPSHOTS</option>';
      d.snapshots.forEach(v => { sel.innerHTML += `<option value="${v}">${v}</option>` });
      setStatus('ready', `✅ ${d.releases.length} versions loaded`);
    }
  } catch(e) {
    sel.innerHTML = '<option value="">Failed to load (offline)</option>';
    setStatus('error', '⚠️ Could not fetch versions');
  }
}

// ─── RAM Slider ───
document.getElementById('ramSlider').addEventListener('input', function() {
  document.getElementById('ramLabel').textContent = this.value + ' MB';
});

// ─── Status ───
function setStatus(type, msg) {
  const dot = document.getElementById('statusDot');
  const title = document.getElementById('statusTitle');
  const small = document.getElementById('statusSmall');
  const msgEl = document.getElementById('statusMsg');
  const colors = {ready:'#06d6a0', launching:'#f59e0b', running:'#00d4ff', error:'#ef4444', idle:'#64748b'};
  const icons = {ready:'🟢', launching:'🟡', running:'🔵', error:'🔴', idle:'⚪'};
  dot.style.background = colors[type] || '#64748b';
  title.textContent = msg;
  small.textContent = msg;
  msgEl.innerHTML = `${icons[type]||'⚪'} ${msg}`;
  msgEl.style.color = colors[type] || '#64748b';
}

// ─── Check Status ───
async function checkStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('statusSmall').textContent = d.message;
    if(d.status === 'idle') setStatus('ready', d.message);
    else if(d.status === 'launching') setStatus('launching', d.message);
    else if(d.status === 'running') setStatus('running', d.message);
    else if(d.status === 'error') setStatus('error', d.message);
  } catch(e) {}
}

// ─── Launch ───
async function launchGame(serverIP) {
  const btn = document.getElementById('playBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Launching...';
  
  const data = {
    username: document.getElementById('username').value || 'Player',
    version: document.getElementById('version').value,
    ram: document.getElementById('ramSlider').value,
    width: document.getElementById('width').value,
    height: document.getElementById('height').value,
    server: serverIP || document.getElementById('server').value || document.getElementById('customServer').value || '',
  };
  
  try {
    const r = await fetch('/api/launch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const res = await r.json();
    if(res.status === 'launching') setStatus('launching', '▶ Launching Minecraft...');
  } catch(e) {
    setStatus('error', '❌ Launch request failed');
  }
  
  // Poll status
  const interval = setInterval(async () => {
    try {
      const r = await fetch('/api/status');
      const d = await r.json();
      if(d.status === 'running') {
        setStatus('running', d.message);
        btn.textContent = '▶ PLAY';
        btn.disabled = false;
        clearInterval(interval);
      } else if(d.status === 'idle') {
        setStatus('ready', d.message);
        btn.textContent = '▶ PLAY';
        btn.disabled = false;
        clearInterval(interval);
      } else if(d.status === 'error') {
        setStatus('error', d.message);
        btn.textContent = '▶ PLAY';
        btn.disabled = false;
        clearInterval(interval);
      }
    } catch(e) { clearInterval(interval); }
  }, 1000);
}

// ─── Auto-save config ───
document.getElementById('username').addEventListener('change', function() {
  fetch('/api/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:this.value})});
});
document.getElementById('server').addEventListener('change', function() {
  fetch('/api/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({server:this.value})});
});
document.getElementById('version').addEventListener('change', function() {
  fetch('/api/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:this.value})});
});
document.getElementById('ramSlider').addEventListener('change', function() {
  fetch('/api/config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ram:parseInt(this.value)})});
});

// ─── Join Server (click from browser) ───
function joinServer(ip) {
  if(!ip) return;
  document.getElementById('server').value = ip;
  setStatus('launching', `🔄 Joining ${ip}...`);
  launchGame(ip);
}

// ─── Init ───
loadVersions();
setInterval(checkStatus, 2000);

// Load saved config
fetch('/api/config').then(r=>r.json()).then(d=>{
  if(d.username) document.getElementById('username').value = d.username;
  if(d.server) document.getElementById('server').value = d.server;
  if(d.version) document.getElementById('version').value = d.version;
  if(d.ram) { document.getElementById('ramSlider').value = d.ram; document.getElementById('ramLabel').textContent = d.ram+' MB'; }
  if(d.width) document.getElementById('width').value = d.width;
  if(d.height) document.getElementById('height').value = d.height;
});
</script>
</body>
</html>'''

# ─── HTTP Server ────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        elif self.path == '/api/versions':
            self.send_json(self.get_versions())
        elif self.path == '/api/status':
            self.send_json(launch_status)
        elif self.path == '/api/config':
            self.send_json(config.data)
        elif self.path == '/api/open-mods':
            os.startfile(MINECRAFT_DIR/"mods")
            self.send_json({"ok":True})
        elif self.path == '/api/open-minecraft':
            os.startfile(MINECRAFT_DIR)
            self.send_json({"ok":True})
        else:
            self.send_response(404); self.end_headers(); self.wfile.write(b'404')
    
    def do_POST(self):
        if self.path == '/api/launch':
            length = int(self.headers.get('Content-Length',0))
            data = json.loads(self.rfile.read(length))
            res = launch_minecraft(data)
            self.send_json(res)
        elif self.path == '/api/config':
            length = int(self.headers.get('Content-Length',0))
            data = json.loads(self.rfile.read(length))
            for k,v in data.items(): config.s(k,v)
            self.send_json({"ok":True})
        else:
            self.send_response(404); self.end_headers(); self.wfile.write(b'404')
    
    def get_versions(self):
        if not vm.manifest: vm.fetch()
        vl = vm.get_list()
        releases = [v["id"] for v in vl if v["type"]=="release"]
        snapshots = [v["id"] for v in vl if v["type"]=="snapshot"]
        return {"success":True,"releases":releases,"snapshots":snapshots}
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args): pass

def start_server():
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f"\n  ╔═══════════════════════════════════════════╗")
    print(f"  ║     A2Launcher v{VERSION}                    ║")
    print(f"  ║  Minecraft Launcher by {AUTHORS}  ║")
    print(f"  ╚═══════════════════════════════════════════╝")
    print(f"\n  🌐 Open in browser: http://127.0.0.1:{PORT}")
    print(f"  📱 Press Ctrl+C to stop\n")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == '__main__':
    # Pre-fetch versions in background
    threading.Thread(target=lambda: vm.fetch() or None, daemon=True).start()
    start_server()
