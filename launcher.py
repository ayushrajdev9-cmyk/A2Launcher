#!/usr/bin/env python3
"""
A2Launcher - Minecraft Launcher by Ayush Rajdev & Anzar Iqbal
GitHub: https://github.com/ayushrajdev9-cmyk/A2Launcher
Description: Premium Minecraft launcher with modern UI, version management,
             mod loader support, offline mode, and game optimization.
             Like TLauncher but built from scratch in Python.
"""

import os, sys, json, time, subprocess, platform, threading, webbrowser, re, struct
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import requests

VERSION = "2.0.0"
AUTHORS = "Ayush Rajdev & Anzar Iqbal"
BASE_DIR = Path.home() / ".a2launcher"
VERSIONS_DIR = BASE_DIR / "versions"
MINECRAFT_DIR = Path.home() / "AppData" / "Roaming" / ".minecraft"
CONFIG_FILE = BASE_DIR / "config.json"
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

for d in [BASE_DIR, VERSIONS_DIR, MINECRAFT_DIR / "mods"]:
    d.mkdir(parents=True, exist_ok=True)

# ─── CONFIG ──────────────────────────────────────────────────
class Config:
    def __init__(self):
        self.data = self.load()
    def load(self):
        if CONFIG_FILE.exists():
            try: return json.load(open(CONFIG_FILE))
            except: pass
        return {"username":"Player","ram":2048,"width":854,"height":480,"java_path":"","version":"latest_release","server":"","jvm":"-XX:+UseG1GC -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M"}
    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.data, open(CONFIG_FILE, "w"), indent=2)
    def get(self, k, d=None): return self.data.get(k, d)
    def set(self, k, v): self.data[k]=v; self.save()

config = Config()

# ─── VERSION MANAGER ─────────────────────────────────────────
class VersionManager:
    def __init__(self):
        self.manifest = None
        self.versions = []
    def fetch(self):
        try:
            r = requests.get(MANIFEST_URL, timeout=15)
            if r.status_code == 200:
                self.manifest = r.json()
                self.versions = self.manifest.get("versions", [])
                return True
        except: pass
        return False
    def get_list(self):
        if not self.manifest: self.fetch()
        return [v for v in self.versions if v["type"] in ["release","snapshot"]]
    def get_json(self, vid):
        p = VERSIONS_DIR / vid / f"{vid}.json"
        if p.exists(): return json.load(open(p))
        url = next((v["url"] for v in self.versions if v["id"]==vid), None)
        if not url: return None
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                (VERSIONS_DIR/vid).mkdir(exist_ok=True)
                json.dump(r.json(), open(p,"w"), indent=2)
                return r.json()
        except: pass
        return None
    def get_installed(self):
        return [d.name for d in VERSIONS_DIR.iterdir() if d.is_dir() and (d/f"{d.name}.jar").exists()]

vm = VersionManager()

# ─── MODERN UI ───────────────────────────────────────────────
class A2Launcher:
    def __init__(self, root):
        self.root = root
        root.title(f"A2Launcher v{VERSION}")
        root.geometry("960x680")
        root.minsize(900, 620)
        try: root.iconbitmap(default="assets/icon.ico")
        except: pass

        # Color palette
        self.c = {
            "bg": "#0b0e14",
            "surface": "#131820",
            "surface2": "#1a2230",
            "surface3": "#222d3d",
            "accent": "#00d4ff",
            "accent2": "#7c3aed",
            "accent3": "#06d6a0",
            "text": "#f0f4f8",
            "text2": "#8892a4",
            "text3": "#4a5568",
            "success": "#06d6a0",
            "danger": "#ef4444",
            "warning": "#f59e0b",
            "border": "#1e293b",
            "hover": "#1e3a5f",
            "card": "#0f172a",
        }
        root.configure(bg=self.c["bg"])

        # Variables
        self.username = tk.StringVar(value=config.get("username","Player"))
        self.ram = tk.IntVar(value=config.get("ram",2048))
        self.width = tk.IntVar(value=config.get("width",854))
        self.height = tk.IntVar(value=config.get("height",480))
        self.server = tk.StringVar(value=config.get("server",""))
        self.version = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.jvm = tk.StringVar(value=config.get("jvm",""))
        self.versions_list = []
        self.loading = False

        self.build_ui()
        self.load_versions()

    def styled(self, parent, cls=tk.Frame, **kw):
        kw.setdefault("bg", self.c["surface"])
        return cls(parent, **kw)

    def build_ui(self):
        # ─── HEADER ───
        hdr = tk.Frame(self.root, bg=self.c["surface2"], height=90)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Gradient-like header bar
        bar = tk.Frame(hdr, bg=self.c["accent"], height=3)
        bar.pack(fill="x")
        
        inner = tk.Frame(hdr, bg=self.c["surface2"])
        inner.pack(fill="both", expand=True, padx=25, pady=12)

        tk.Label(inner, text="⛏ A2Launcher", font=("Segoe UI", 26, "bold"),
                fg=self.c["accent"], bg=self.c["surface2"]).pack(side="left")
        
        badge = tk.Frame(inner, bg=self.c["accent2"], padx=10, pady=2)
        badge.pack(side="left", padx=(12,0), pady=5)
        tk.Label(badge, text=f"v{VERSION}", font=("Segoe UI", 9, "bold"),
                fg="#fff", bg=self.c["accent2"]).pack()
        
        cred = tk.Frame(inner, bg=self.c["surface2"])
        cred.pack(side="left", padx=(15,0))
        tk.Label(cred, text="by", font=("Segoe UI", 9), fg=self.c["text2"],
                bg=self.c["surface2"]).pack(side="left")
        tk.Label(cred, text="Ayush Rajdev & Anzar Iqbal", font=("Segoe UI", 9, "bold"),
                fg=self.c["text"], bg=self.c["surface2"]).pack(side="left", padx=(4,0))

        # GitHub button
        gh_btn = tk.Button(inner, text="★ GitHub", font=("Segoe UI", 10, "bold"),
                          bg=self.c["surface3"], fg=self.c["text"], relief="flat",
                          cursor="hand2", padx=15, pady=6,
                          activebackground=self.c["hover"],
                          command=lambda: webbrowser.open("https://github.com/ayushrajdev9-cmyk/A2Launcher"))
        gh_btn.pack(side="right")
        self.hover(gh_btn, self.c["hover"])

        # ─── MAIN BODY ───
        body = tk.Frame(self.root, bg=self.c["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=(15,10))

        # LEFT SIDEBAR
        left = tk.Frame(body, bg=self.c["card"], width=220)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self.sidebar_button(left, "🏠 Dashboard", 0).pack(fill="x", padx=8, pady=(12,2))
        self.sidebar_button(left, "📦 Versions", 1).pack(fill="x", padx=8, pady=2)
        self.sidebar_button(left, "🔧 Mod Loaders", 2).pack(fill="x", padx=8, pady=2)
        self.sidebar_button(left, "🎨 Skins", 3).pack(fill="x", padx=8, pady=2)
        self.sidebar_button(left, "⚙ Settings", 4).pack(fill="x", padx=8, pady=(2,12))

        # CENTER CONTENT
        center = tk.Frame(body, bg=self.c["bg"])
        center.pack(side="left", fill="both", expand=True, padx=(15,0))

        # ─── USERNAME ROW ───
        row1 = tk.Frame(center, bg=self.c["bg"])
        row1.pack(fill="x", pady=(0,10))
        
        ulbl = tk.Frame(row1, bg=self.c["surface"], padx=18, pady=8)
        ulbl.pack(side="left", fill="x", expand=True)
        tk.Label(ulbl, text="👤  Username", font=("Segoe UI", 10),
                fg=self.c["text2"], bg=self.c["surface"]).pack(anchor="w")
        e = tk.Entry(ulbl, textvariable=self.username, font=("Segoe UI", 14, "bold"),
                    bg=self.c["bg"], fg=self.c["text"], relief="flat",
                    insertbackground=self.c["accent"], bd=0)
        e.pack(fill="x", ipady=3, pady=(2,0))
        e.bind("<KeyRelease>", lambda e: config.set("username", self.username.get()))

        # Quick server
        srv = tk.Frame(row1, bg=self.c["surface"], padx=18, pady=8)
        srv.pack(side="right", padx=(10,0), fill="x", expand=True)
        tk.Label(srv, text="🔗  Server IP", font=("Segoe UI", 10),
                fg=self.c["text2"], bg=self.c["surface"]).pack(anchor="w")
        se = tk.Entry(srv, textvariable=self.server, font=("Segoe UI", 12),
                     bg=self.c["bg"], fg=self.c["text"], relief="flat",
                     insertbackground=self.c["accent"], bd=0)
        se.pack(fill="x", ipady=3, pady=(2,0))
        se.bind("<KeyRelease>", lambda e: config.set("server", self.server.get()))

        # ─── VERSION + LAUNCH ───
        card = tk.Frame(center, bg=self.c["surface"], padx=25, pady=20)
        card.pack(fill="x", pady=(0,12))

        tk.Label(card, text="🚀  Launch Minecraft", font=("Segoe UI", 18, "bold"),
                fg=self.c["text"], bg=self.c["surface"]).pack(anchor="w")

        ver_row = tk.Frame(card, bg=self.c["surface"])
        ver_row.pack(fill="x", pady=(15,0))

        # Version selector
        vf = tk.Frame(ver_row, bg=self.c["surface"])
        vf.pack(side="left", fill="x", expand=True)
        tk.Label(vf, text="MINECRAFT VERSION", font=("Segoe UI", 8, "bold"),
                fg=self.c["text3"], bg=self.c["surface"]).pack(anchor="w")
        
        vsel = tk.Frame(vf, bg=self.c["bg"], padx=10, pady=2)
        vsel.pack(fill="x", pady=(3,0))
        self.version_combo = ttk.Combobox(vsel, textvariable=self.version,
                                          font=("Segoe UI", 12), height=20)
        self.version_combo.pack(fill="x", ipady=5, pady=2)
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: config.set("version", self.version.get()))

        # RAM slider
        rf = tk.Frame(ver_row, bg=self.c["surface"])
        rf.pack(side="left", padx=(20,0))
        tk.Label(rf, text="RAM (MB)", font=("Segoe UI", 8, "bold"),
                fg=self.c["text3"], bg=self.c["surface"]).pack(anchor="w")
        ram_frame = tk.Frame(rf, bg=self.c["bg"], padx=12, pady=5)
        ram_frame.pack()
        self.ram_label = tk.Label(ram_frame, text=f"{self.ram.get()} MB",
                                  font=("Segoe UI", 16, "bold"),
                                  fg=self.c["accent"], bg=self.c["bg"])
        self.ram_label.pack()
        ram_slider = ttk.Scale(rf, from_=512, to=16384, value=self.ram.get(),
                               orient="horizontal", length=120,
                               command=self.update_ram)
        ram_slider.pack(pady=(3,0))

        # Resolution
        resf = tk.Frame(ver_row, bg=self.c["surface"])
        resf.pack(side="left", padx=(20,0))
        tk.Label(resf, text="RESOLUTION", font=("Segoe UI", 8, "bold"),
                fg=self.c["text3"], bg=self.c["surface"]).pack(anchor="w")
        resi = tk.Frame(resf, bg=self.c["bg"], padx=10, pady=5)
        resi.pack()
        tk.Label(resi, text="W", font=("Segoe UI", 9), fg=self.c["text2"],
                bg=self.c["bg"]).pack(side="left")
        we = tk.Entry(resi, textvariable=self.width, width=4,
                      font=("Segoe UI", 12, "bold"), bg=self.c["surface"],
                      fg=self.c["text"], relief="flat", bd=0, justify="center")
        we.pack(side="left", padx=3)
        tk.Label(resi, text="×", font=("Segoe UI", 12, "bold"),
                fg=self.c["text2"], bg=self.c["bg"]).pack(side="left")
        he = tk.Entry(resi, textvariable=self.height, width=4,
                      font=("Segoe UI", 12, "bold"), bg=self.c["surface"],
                      fg=self.c["text"], relief="flat", bd=0, justify="center")
        he.pack(side="left", padx=3)

        # ─── LAUNCH BUTTON ───
        lf = tk.Frame(center, bg=self.c["bg"])
        lf.pack(fill="x", pady=(5,10))

        self.launch_btn = tk.Button(lf, text="▶  PLAY", font=("Segoe UI", 18, "bold"),
                                   bg=self.c["accent"], fg="#000",
                                   relief="flat", cursor="hand2",
                                   padx=40, pady=14, bd=0,
                                   activebackground="#00e5ff",
                                   command=self.launch_game)
        self.launch_btn.pack(fill="x")
        self.launch_btn.bind("<Enter>", lambda e: self.launch_btn.config(bg="#00e5ff"))
        self.launch_btn.bind("<Leave>", lambda e: self.launch_btn.config(bg=self.c["accent"]))

        # Status bar
        st = tk.Frame(self.root, bg=self.c["surface2"], height=32)
        st.pack(fill="x")
        st.pack_propagate(False)
        tk.Label(st, textvariable=self.status, font=("Segoe UI", 9),
                fg=self.c["text2"], bg=self.c["surface2"]).pack(side="left", padx=20, pady=5)
        tk.Label(st, text=f"{AUTHORS}", font=("Segoe UI", 8),
                fg=self.c["text3"], bg=self.c["surface2"]).pack(side="right", padx=20, pady=5)

        # ─── MOD LOADER QUICK ACTIONS ───
        qa = tk.Frame(center, bg=self.c["surface"], padx=20, pady=12)
        qa.pack(fill="x", pady=(0,0))

        tk.Label(qa, text="⚡ Quick Actions", font=("Segoe UI", 12, "bold"),
                fg=self.c["text"], bg=self.c["surface"]).pack(anchor="w")
        
        qb = tk.Frame(qa, bg=self.c["surface"])
        qb.pack(fill="x", pady=(8,0))

        for text, cmd in [
            ("📦 Install Forge", lambda: webbrowser.open("https://files.minecraftforge.net/")),
            ("🧵 Install Fabric", lambda: webbrowser.open("https://fabricmc.net/use/")),
            ("✨ Install OptiFine", lambda: webbrowser.open("https://optifine.net/downloads")),
            ("📂 Open Mods Folder", lambda: [os.startfile(MINECRAFT_DIR/"mods"), self.set_status("📂 Mods folder opened")]),
            ("📂 Open .minecraft", lambda: [os.startfile(MINECRAFT_DIR), self.set_status("📂 .minecraft opened")]),
            ("🔄 Refresh Versions", self.load_versions),
        ]:
            btn = tk.Button(qb, text=text, font=("Segoe UI", 9, "bold"),
                          bg=self.c["surface3"], fg=self.c["text"],
                          relief="flat", cursor="hand2", padx=12, pady=6,
                          activebackground=self.c["hover"], command=cmd)
            btn.pack(side="left", padx=3)
            self.hover(btn, self.c["hover"])

    def sidebar_button(self, parent, text, idx):
        f = tk.Frame(parent, bg=self.c["card"], cursor="hand2")
        lbl = tk.Label(f, text=text, font=("Segoe UI", 11), fg=self.c["text2"],
                      bg=self.c["card"], padx=12, pady=8, anchor="w")
        lbl.pack(fill="x")
        def on_enter(e):
            f.config(bg=self.c["surface3"])
            lbl.config(bg=self.c["surface3"])
        def on_leave(e):
            f.config(bg=self.c["card"])
            lbl.config(bg=self.c["card"])
        f.bind("<Enter>", on_enter)
        f.bind("<Leave>", on_leave)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)
        lbl.bind("<Button-1>", lambda e: self.sidebar_click(idx))
        return f

    def sidebar_click(self, idx):
        actions = [
            lambda: self.set_status("🏠 Dashboard - Select a version to play"),
            lambda: self.load_versions(),
            lambda: webbrowser.open("https://files.minecraftforge.net/"),
            lambda: self.set_status("🎨 Skin changer coming in next update!"),
            lambda: self.set_status("⚙ Settings - Edit config.json manually"),
        ]
        if idx < len(actions): actions[idx]()

    def hover(self, widget, color):
        widget.bind("<Enter>", lambda e: widget.config(bg=color))
        widget.bind("<Leave>", lambda e: widget.config(bg=self.c["surface3"]))

    def set_status(self, text):
        self.status.set(text)
        self.root.update()

    def update_ram(self, val):
        v = int(float(val))
        self.ram.set(v)
        self.ram_label.config(text=f"{v} MB")
        config.set("ram", v)

    def load_versions(self):
        if self.loading: return
        self.loading = True
        self.set_status("📥 Fetching Minecraft versions...")
        self.root.update()
        def fetch():
            ok = vm.fetch()
            self.root.after(0, lambda: self.on_versions(ok))
        threading.Thread(target=fetch, daemon=True).start()

    def on_versions(self, ok):
        self.loading = False
        if ok:
            vl = vm.get_list()
            self.versions_list = vl
            releases = [v["id"] for v in vl if v["type"]=="release"]
            snapshots = [v["id"] for v in vl if v["type"]=="snapshot"]
            display = ["latest_release", "latest_snapshot"] + releases + ["─"*20 + " SNAPSHOTS"] + snapshots
            self.version_combo["values"] = display
            sv = config.get("version","latest_release")
            self.version.set(sv if sv in display else "latest_release")
            self.set_status(f"✅ {len(releases)} releases, {len(snapshots)} snapshots loaded")
        else:
            self.set_status("⚠️  Failed to fetch versions (check internet)")
            self.version_combo["values"] = ["offline"]
            self.version.set("offline")

    def find_java(self, version_id):
        cfg = config.get("java_path","")
        if cfg and os.path.exists(cfg): return cfg
        # Determine Java version needed
        try:
            parts = version_id.split(".")
            if version_id.startswith("1.") and len(parts) > 1:
                sub = int(parts[1])
                maj = 17 if sub >= 18 else (11 if sub >= 16 else 8)
            else: maj = 17
        except: maj = 17
        # Search
        paths = [os.environ.get("JAVA_HOME","")]
        for pf in [os.environ.get("ProgramFiles","C:\\Program Files"),
                   os.environ.get("ProgramFiles(x86)","C:\\Program Files (x86)")]:
            if os.path.exists(pf):
                for d in os.listdir(pf):
                    if any(x in d.lower() for x in ["java","jdk","jre","adopt","semeru"]):
                        j = os.path.join(pf, d, "bin", "javaw.exe")
                        if os.path.exists(j): paths.append(j)
        paths += [
            r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
            r"C:\Program Files\Java\jdk-21\bin\javaw.exe",
        ]
        for p in paths:
            if p and os.path.exists(p):
                config.set("java_path", p)
                return p
        try:
            subprocess.run(["java","-version"], capture_output=True, timeout=5)
            config.set("java_path","java")
            return "java"
        except: pass
        return None

    def launch_game(self):
        name = self.username.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter a username!")
            return

        vid = self.version.get()
        if vid == "latest_release":
            for v in self.versions_list:
                if v["type"]=="release": vid=v["id"]; break
        elif vid == "latest_snapshot":
            for v in self.versions_list:
                if v["type"]=="snapshot": vid=v["id"]; break

        self.set_status(f"🚀 Launching Minecraft {vid}...")
        self.launch_btn.config(state="disabled", text="⏳ Launching...")
        self.root.update()

        def thread():
            try:
                vj = vm.get_json(vid)
                if not vj:
                    self.root.after(0, lambda: self.launch_error(f"Version {vid} not found"))
                    return
                java = self.find_java(vid)
                if not java:
                    self.root.after(0, lambda: self.launch_error("Java not found!\nInstall from adoptium.net"))
                    return
                ram_mb = self.ram.get()
                w, h = self.width.get(), self.height.get()
                
                # Build classpath
                cp = []
                client_jar = VERSIONS_DIR / vid / f"{vid}.jar"
                if client_jar.exists(): cp.append(str(client_jar))
                lib_dir = BASE_DIR / "libraries"
                for lib in vj.get("libraries",[]):
                    art = lib.get("downloads",{}).get("artifact",{})
                    lp = lib_dir / art.get("path","")
                    if lp.exists(): cp.append(str(lp))
                
                sep = ";" if platform.system()=="Windows" else ":"
                natives = str(BASE_DIR / "natives" / vid)
                os.makedirs(natives, exist_ok=True)
                main = vj.get("mainClass","net.minecraft.client.main.Main")
                jvm_args = self.jvm.get().split() if self.jvm.get() else []
                
                args = [f"-Xmx{ram_mb}M", f"-Xms{ram_mb//2}M"] + jvm_args + [
                    "-Djava.library.path="+natives, "-cp", sep.join(cp),
                    main,
                    "--username", name,
                    "--version", vid,
                    "--gameDir", str(MINECRAFT_DIR),
                    "--assetsDir", str(BASE_DIR/"assets"),
                    "--assetIndex", vj.get("assetIndex",{}).get("id","legacy"),
                    "--uuid", "00000000-0000-0000-0000-000000000000",
                    "--accessToken", "0", "--userType", "mojang",
                    "--versionType", vj.get("type","release"),
                    "--width", str(w), "--height", str(h),
                ]
                
                self.root.after(0, lambda: self.set_status(f"▶ Running Minecraft {vid}... Close game to return"))
                subprocess.Popen([java]+args, cwd=str(MINECRAFT_DIR),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
            except Exception as e:
                self.root.after(0, lambda: self.launch_error(f"Error: {str(e)}"))
            finally:
                self.root.after(0, self.launch_reset)

        threading.Thread(target=thread, daemon=True).start()

    def launch_error(self, msg):
        messagebox.showerror("Launch Error", msg)
        self.set_status(f"❌ {msg[:40]}...")

    def launch_reset(self):
        self.launch_btn.config(state="normal", text="▶  PLAY")
        self.set_status("✅ Game closed. Ready to launch again.")

if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════╗
    ║     A2Launcher v{VERSION}                    ║
    ║  Minecraft Launcher by {AUTHORS}  ║
    ╚═══════════════════════════════════════════╝
    """)
    root = tk.Tk()
    app = A2Launcher(root)
    root.mainloop()
