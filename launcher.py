#!/usr/bin/env python3
"""
A2Launcher - Minecraft Launcher by Ayush Rajdev & Anzar Iqbal
GitHub: https://github.com/ayushrajdev9-cmyk/A2Launcher
Description: Custom Minecraft launcher with version management,
             mod loader support, offline login, and game utilities.
             Like TLauncher but built from scratch in Python.
"""

import os
import sys
import json
import time
import subprocess
import platform
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import requests
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False
    print("[!] tkinter not available. Using CLI mode.")

# ─── Constants ────────────────────────────────────────────────

VERSION = "1.0.0"
AUTHORS = "Ayush Rajdev & Anzar Iqbal"
LAUNCHER_NAME = "A2Launcher"

BASE_DIR = Path.home() / ".mclauncher"
VERSIONS_DIR = BASE_DIR / "versions"
MODS_DIR = BASE_DIR / "mods"
INSTANCES_DIR = BASE_DIR / "instances"
JAVA_DIR = BASE_DIR / "java"
CONFIG_FILE = BASE_DIR / "config.json"
MINECRAFT_DIR = Path.home() / "AppData" / "Roaming" / ".minecraft"

# Mojang API endpoints
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ASSETS_URL_TEMPLATE = "https://resources.download.minecraft.net/{}/{}"
LIBRARIES_BASE = "https://libraries.minecraft.net/"
RESOURCES_BASE = "https://resources.download.minecraft.net/"

os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(MODS_DIR, exist_ok=True)
os.makedirs(INSTANCES_DIR, exist_ok=True)
os.makedirs(JAVA_DIR, exist_ok=True)
os.makedirs(BASE_DIR / "skins", exist_ok=True)

# ─── Config Manager ───────────────────────────────────────────

class Config:
    def __init__(self):
        self.data = self.load()
    
    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {
            "username": "Player",
            "ram": "2048",
            "resolution_width": "854",
            "resolution_height": "480",
            "java_path": "",
            "version": "latest_release",
            "theme": "dark",
            "server_ip": "",
            "jvm_args": "-XX:+UseG1GC -Dsun.rmi.dgc.server.gcInterval=2147483646 -XX:+UnlockExperimentalVMOptions -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M"
        }
    
    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.save()

config = Config()

# ─── Minecraft Version Manager ────────────────────────────────

class VersionManager:
    def __init__(self):
        self.manifest = None
        self.versions = []
        self.loaded_versions = []
    
    def fetch_manifest(self):
        """Fetch version manifest from Mojang"""
        try:
            resp = requests.get(MANIFEST_URL, timeout=15)
            if resp.status_code == 200:
                self.manifest = resp.json()
                self.versions = self.manifest.get("versions", [])
                return True
        except:
            pass
        return False
    
    def get_version_list(self):
        """Get formatted version list"""
        if not self.manifest:
            self.fetch_manifest()
        versions = []
        for v in self.versions:
            if v["type"] in ["release", "snapshot"]:
                versions.append(v)
        return versions
    
    def get_version_json(self, version_id):
        """Download version JSON"""
        version_path = VERSIONS_DIR / version_id
        json_file = version_path / f"{version_id}.json"
        
        if json_file.exists():
            with open(json_file) as f:
                return json.load(f)
        
        # Find version URL
        version_url = None
        for v in self.versions:
            if v["id"] == version_id:
                version_url = v["url"]
                break
        
        if not version_url:
            return None
        
        try:
            resp = requests.get(version_url, timeout=15)
            if resp.status_code == 200:
                version_path.mkdir(parents=True, exist_ok=True)
                with open(json_file, "w") as f:
                    f.write(resp.text)
                return resp.json()
        except:
            pass
        return None
    
    def get_download_size(self, version_id):
        """Get total download size for a version"""
        vjson = self.get_version_json(version_id)
        if not vjson:
            return 0
        total = 0
        for lib in vjson.get("libraries", []):
            if "downloads" in lib:
                artifact = lib["downloads"].get("artifact", {})
                total += artifact.get("size", 0)
        client = vjson.get("downloads", {}).get("client", {})
        total += client.get("size", 0)
        return total
    
    def get_installed_versions(self):
        """List locally installed versions"""
        installed = []
        for d in VERSIONS_DIR.iterdir():
            if d.is_dir():
                jar_file = d / f"{d.name}.jar"
                if jar_file.exists():
                    installed.append(d.name)
        return installed

    def get_java_args(self, version_id, username, ram_mb, resolution, jvm_args=""):
        """Generate Java launch arguments"""
        vjson = self.get_version_json(version_id)
        if not vjson:
            return []
        
        width, height = resolution
        # Build classpath
        classpath_parts = []
        natives_dir = str(BASE_DIR / "natives" / version_id)
        os.makedirs(natives_dir, exist_ok=True)
        
        # Minecraft client jar
        client_jar = VERSIONS_DIR / version_id / f"{version_id}.jar"
        if client_jar.exists():
            classpath_parts.append(str(client_jar))
        
        # Library jars
        lib_dir = BASE_DIR / "libraries"
        for lib in vjson.get("libraries", []):
            if "downloads" in lib:
                artifact = lib["downloads"].get("artifact", {})
                path = artifact.get("path", "")
                lib_path = lib_dir / path
                if lib_path.exists():
                    classpath_parts.append(str(lib_path))
        
        classpath = ";".join(classpath_parts) if platform.system() == "Windows" else ":".join(classpath_parts)
        
        main_class = vjson.get("mainClass", "net.minecraft.client.main.Main")
        
        args = [
            f"-Xmx{ram_mb}M",
            f"-Xms{ram_mb // 2}M",
        ]
        
        # Add custom JVM args
        if jvm_args:
            args.extend(jvm_args.split())
        
        args.extend([
            "-Djava.library.path=" + natives_dir,
            "-cp", classpath,
            main_class,
            "--username", username,
            "--version", version_id,
            "--gameDir", str(MINECRAFT_DIR),
            "--assetsDir", str(BASE_DIR / "assets"),
            "--assetIndex", vjson.get("assetIndex", {}).get("id", "legacy"),
            "--uuid", "00000000-0000-0000-0000-000000000000",
            "--accessToken", "0",
            "--userType", "mojang",
            "--versionType", vjson.get("type", "release"),
            "--width", str(width),
            "--height", str(height),
        ])
        
        return args

vm = VersionManager()

# ─── GUI Launcher ─────────────────────────────────────────────

if TK_AVAILABLE:
    class MinecraftLauncher:
        def __init__(self, root):
            self.root = root
            self.root.title(f"{LAUNCHER_NAME} v{VERSION} - by {AUTHORS}")
            self.root.geometry("900x650")
            self.root.minsize(800, 550)
            
            # Set icon
            try:
                self.root.iconbitmap(default="assets/icon.ico") if os.path.exists("assets/icon.ico") else None
            except:
                pass
            
            # Colors
            self.colors = {
                "bg": "#1a1a2e",
                "bg2": "#16213e",
                "accent": "#00e5ff",
                "text": "#ffffff",
                "text2": "#a0a0b0",
                "success": "#00ff88",
                "error": "#ff4444",
                "button": "#0f3460",
                "button_hover": "#1a5276",
                "card": "#0d1117",
            }
            
            self.root.configure(bg=self.colors["bg"])
            
            # Variables
            self.username_var = tk.StringVar(value=config.get("username", "Player"))
            self.ram_var = tk.StringVar(value=config.get("ram", "2048"))
            self.width_var = tk.StringVar(value=config.get("resolution_width", "854"))
            self.height_var = tk.StringVar(value=config.get("resolution_height", "480"))
            self.server_var = tk.StringVar(value=config.get("server_ip", ""))
            self.version_var = tk.StringVar()
            self.jvm_args_var = tk.StringVar(value=config.get("jvm_args", ""))
            self.status_var = tk.StringVar(value="Ready to launch ✓")
            
            self.versions_list = []
            self.loading = False
            
            self.build_ui()
            self.load_versions()
        
        def build_ui(self):
            """Build the launcher interface"""
            # Main container
            main_container = tk.Frame(self.root, bg=self.colors["bg"])
            main_container.pack(fill="both", expand=True)
            
            # ─── Header ───
            header = tk.Frame(main_container, bg=self.colors["bg2"], height=80)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            title_frame = tk.Frame(header, bg=self.colors["bg2"])
            title_frame.pack(side="left", padx=20, pady=10)
            
            tk.Label(title_frame, text=f"⛏️ {LAUNCHER_NAME}", 
                    font=("Segoe UI", 22, "bold"), 
                    fg=self.colors["accent"], bg=self.colors["bg2"]).pack(anchor="w")
            tk.Label(title_frame, text=f"by {AUTHORS}", 
                    font=("Segoe UI", 10), 
                    fg=self.colors["text2"], bg=self.colors["bg2"]).pack(anchor="w")
            
            # Social buttons
            social_frame = tk.Frame(header, bg=self.colors["bg2"])
            social_frame.pack(side="right", padx=20)
            
            self.create_button(social_frame, "🐙 GitHub", self.open_github, 
                             bg=self.colors["button"], width=10)
            
            # ─── Main Content Area ───
            content = tk.Frame(main_container, bg=self.colors["bg"])
            content.pack(fill="both", expand=True, padx=20, pady=15)
            
            # Left panel - News/Server
            left_panel = tk.Frame(content, bg=self.colors["card"], width=250)
            left_panel.pack(side="left", fill="y", padx=(0, 10))
            left_panel.pack_propagate(False)
            
            tk.Label(left_panel, text="📰 News", 
                    font=("Segoe UI", 14, "bold"),
                    fg=self.colors["accent"], bg=self.colors["card"]).pack(pady=(15, 5))
            
            news_text = tk.Text(left_panel, bg=self.colors["bg"], fg=self.colors["text2"],
                               font=("Segoe UI", 9), relief="flat", height=12,
                               wrap="word", padx=10, pady=5)
            news_text.insert("1.0", f"🎮 {LAUNCHER_NAME} v{VERSION} released!\n\n"
                                    f"✅ Created by {AUTHORS}\n\n"
                                    f"🔧 Features:\n"
                                    f"• Version manager\n"
                                    f"• Mod loader support\n"
                                    f"• Offline/online mode\n"
                                    f"• RAM optimization\n"
                                    f"• Custom resolution\n"
                                    f"• Server direct connect\n\n"
                                    f"⭐ Star us on GitHub!")
            news_text.config(state="disabled")
            news_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            # Quick server connect
            tk.Label(left_panel, text="🔗 Quick Connect", 
                    font=("Segoe UI", 12, "bold"),
                    fg=self.colors["text"], bg=self.colors["card"]).pack(pady=(5, 5))
            
            server_entry = tk.Entry(left_panel, textvariable=self.server_var,
                                   bg=self.colors["bg"], fg=self.colors["text"],
                                   font=("Segoe UI", 10), relief="flat",
                                   insertbackground=self.colors["text"])
            server_entry.pack(padx=10, fill="x", ipady=4)
            server_entry.insert(0, config.get("server_ip", ""))
            
            self.create_button(left_panel, "▶ Join Server", self.join_server, 
                             bg="#00c853", width=20).pack(pady=(5, 15))
            
            # ─── Center Panel - Main controls ───
            center = tk.Frame(content, bg=self.colors["bg"])
            center.pack(side="left", fill="both", expand=True)
            
            # Username
            user_frame = tk.Frame(center, bg=self.colors["bg"])
            user_frame.pack(fill="x", pady=(0, 10))
            tk.Label(user_frame, text="👤 Username", 
                    font=("Segoe UI", 11), fg=self.colors["text"], 
                    bg=self.colors["bg"]).pack(anchor="w")
            username_entry = tk.Entry(user_frame, textvariable=self.username_var,
                                     bg=self.colors["card"], fg=self.colors["text"],
                                     font=("Segoe UI", 12), relief="flat",
                                     insertbackground=self.colors["text"])
            username_entry.pack(fill="x", ipady=6, pady=(3, 0))
            username_entry.bind("<KeyRelease>", lambda e: config.set("username", self.username_var.get()))
            
            # Version selector
            ver_frame = tk.Frame(center, bg=self.colors["bg"])
            ver_frame.pack(fill="x", pady=(0, 10))
            tk.Label(ver_frame, text="📦 Minecraft Version", 
                    font=("Segoe UI", 11), fg=self.colors["text"], 
                    bg=self.colors["bg"]).pack(anchor="w")
            
            ver_select_frame = tk.Frame(ver_frame, bg=self.colors["bg"])
            ver_select_frame.pack(fill="x", pady=(3, 0))
            
            self.version_combo = ttk.Combobox(ver_select_frame, textvariable=self.version_var,
                                              font=("Segoe UI", 11),
                                              state="readonly", height=20)
            self.version_combo.pack(side="left", fill="x", expand=True, ipady=4)
            self.version_combo.bind("<<ComboboxSelected>>", self.on_version_change)
            
            self.refresh_btn = self.create_button(ver_select_frame, "🔄", self.load_versions, 
                                                 bg=self.colors["button"], width=3)
            self.refresh_btn.pack(side="right", padx=(5, 0))
            
            # RAM Slider
            ram_frame = tk.Frame(center, bg=self.colors["bg"])
            ram_frame.pack(fill="x", pady=(0, 10))
            tk.Label(ram_frame, text=f"💾 RAM: {self.ram_var.get()} MB", 
                    font=("Segoe UI", 11), fg=self.colors["text"], 
                    bg=self.colors["bg"]).pack(anchor="w")
            
            ram_slider = ttk.Scale(ram_frame, from_=512, to=16384, 
                                  value=int(self.ram_var.get()),
                                  orient="horizontal",
                                  command=lambda v: self.update_ram_label(v, ram_label))
            ram_slider.pack(fill="x", pady=(3, 0))
            
            ram_label = tk.Label(ram_frame, text=f"{self.ram_var.get()} MB",
                                font=("Segoe UI", 9), fg=self.colors["text2"],
                                bg=self.colors["bg"])
            ram_label.pack()
            
            # Resolution
            res_frame = tk.Frame(center, bg=self.colors["bg"])
            res_frame.pack(fill="x", pady=(0, 10))
            tk.Label(res_frame, text="🖥️ Resolution", 
                    font=("Segoe UI", 11), fg=self.colors["text"], 
                    bg=self.colors["bg"]).pack(anchor="w")
            
            res_input_frame = tk.Frame(res_frame, bg=self.colors["bg"])
            res_input_frame.pack(fill="x", pady=(3, 0))
            
            tk.Label(res_input_frame, text="W:", font=("Segoe UI", 10), 
                    fg=self.colors["text2"], bg=self.colors["bg"]).pack(side="left")
            w_entry = tk.Entry(res_input_frame, textvariable=self.width_var,
                              bg=self.colors["card"], fg=self.colors["text"],
                              font=("Segoe UI", 10), width=6, relief="flat",
                              insertbackground=self.colors["text"])
            w_entry.pack(side="left", padx=(3, 10), ipady=3)
            
            tk.Label(res_input_frame, text="H:", font=("Segoe UI", 10), 
                    fg=self.colors["text2"], bg=self.colors["bg"]).pack(side="left")
            h_entry = tk.Entry(res_input_frame, textvariable=self.height_var,
                              bg=self.colors["card"], fg=self.colors["text"],
                              font=("Segoe UI", 10), width=6, relief="flat",
                              insertbackground=self.colors["text"])
            h_entry.pack(side="left", padx=(3, 0), ipady=3)
            
            # JVM Args
            jvm_frame = tk.Frame(center, bg=self.colors["bg"])
            jvm_frame.pack(fill="x", pady=(0, 10))
            tk.Label(jvm_frame, text="⚙️ JVM Arguments (advanced)", 
                    font=("Segoe UI", 11), fg=self.colors["text"], 
                    bg=self.colors["bg"]).pack(anchor="w")
            jvm_entry = tk.Entry(jvm_frame, textvariable=self.jvm_args_var,
                                bg=self.colors["card"], fg=self.colors["text"],
                                font=("Segoe UI", 9), relief="flat",
                                insertbackground=self.colors["text"])
            jvm_entry.pack(fill="x", ipady=4, pady=(3, 0))
            
            # ─── Launch Button + Status ───
            bottom_frame = tk.Frame(center, bg=self.colors["bg"])
            bottom_frame.pack(fill="x", pady=(15, 0))
            
            status_label = tk.Label(bottom_frame, textvariable=self.status_var,
                                   font=("Segoe UI", 9), fg=self.colors["text2"],
                                   bg=self.colors["bg"])
            status_label.pack(anchor="w", pady=(0, 5))
            
            btn_frame = tk.Frame(bottom_frame, bg=self.colors["bg"])
            btn_frame.pack(fill="x")
            
            self.launch_btn = self.create_button(btn_frame, "▶  LAUNCH MINECRAFT", 
                                                self.launch_game,
                                                bg="#00e5ff", fg="#000000",
                                                font_size=14, height=2)
            self.launch_btn.pack(side="left", fill="x", expand=True)
            
            self.create_button(btn_frame, "📂 Open Folder", self.open_minecraft_dir,
                             bg=self.colors["button"], width=12).pack(side="right", padx=(5, 0))
            
            # ─── Right Panel - Mods/Skins ───
            right_panel = tk.Frame(content, bg=self.colors["card"], width=200)
            right_panel.pack(side="right", fill="y", padx=(10, 0))
            right_panel.pack_propagate(False)
            
            tk.Label(right_panel, text="🎨 Skins & Mods", 
                    font=("Segoe UI", 14, "bold"),
                    fg=self.colors["accent"], bg=self.colors["card"]).pack(pady=(15, 10))
            
            self.create_button(right_panel, "👕 Change Skin", self.change_skin,
                             bg=self.colors["button"], width=18).pack(pady=3)
            self.create_button(right_panel, "📦 Install Mods", self.install_mods,
                             bg=self.colors["button"], width=18).pack(pady=3)
            self.create_button(right_panel, "🔧 Install Forge", self.install_forge,
                             bg=self.colors["button"], width=18).pack(pady=3)
            self.create_button(right_panel, "🧵 Install Fabric", self.install_fabric,
                             bg=self.colors["button"], width=18).pack(pady=3)
            self.create_button(right_panel, "✨ Install OptiFine", self.install_optifine,
                             bg=self.colors["button"], width=18).pack(pady=3)
            
            tk.Label(right_panel, text="⚡ Quick Tips", 
                    font=("Segoe UI", 12, "bold"),
                    fg=self.colors["text"], bg=self.colors["card"]).pack(pady=(20, 5))
            
            tips = tk.Text(right_panel, bg=self.colors["bg"], fg=self.colors["text2"],
                          font=("Segoe UI", 8), relief="flat", height=8,
                          wrap="word", padx=8, pady=5)
            tips.insert("1.0", "💡 Tips:\n\n"
                              "• Allocate 2-4GB RAM\n"
                              "  for modded MC\n\n"
                              "• Use OptiFine for\n"
                              "  better FPS\n\n"
                              "• Java 17+ required\n"
                              "  for MC 1.18+\n\n"
                              "• Run as admin if\n"
                              "  launch fails")
            tips.config(state="disabled")
            tips.pack(fill="both", expand=True, padx=5, pady=(0, 10))
            
            # Footer
            footer = tk.Frame(main_container, bg=self.colors["bg2"], height=25)
            footer.pack(fill="x")
            footer.pack_propagate(False)
            
            tk.Label(footer, 
                    text=f"⚡ {LAUNCHER_NAME} v{VERSION} | Created by {AUTHORS} | Open Source Minecraft Launcher",
                    font=("Segoe UI", 8), fg=self.colors["text2"], 
                    bg=self.colors["bg2"]).pack(pady=3)
        
        def create_button(self, parent, text, command, bg=None, fg=None, 
                         font_size=10, width=None, height=1):
            """Create a styled button"""
            btn = tk.Button(parent, text=text, command=command,
                          font=("Segoe UI", font_size, "bold"),
                          bg=bg or self.colors["button"],
                          fg=fg or self.colors["text"],
                          relief="flat", cursor="hand2",
                          activebackground=self.colors["button_hover"],
                          activeforeground=self.colors["text"],
                          bd=0, padx=10, pady=5)
            
            if width:
                btn.config(width=width)
            if height > 1:
                btn.config(pady=8)
            
            # Hover effects
            btn.bind("<Enter>", lambda e: btn.config(bg=self.colors["button_hover"]))
            btn.bind("<Leave>", lambda e: btn.config(bg=bg or self.colors["button"]))
            
            return btn
        
        def load_versions(self):
            """Load Minecraft versions in background"""
            if self.loading:
                return
            self.loading = True
            self.status_var.set("📥 Fetching version list...")
            self.refresh_btn.config(state="disabled")
            self.root.update()
            
            def fetch():
                success = vm.fetch_manifest()
                self.root.after(0, lambda: self.on_versions_loaded(success))
            
            threading.Thread(target=fetch, daemon=True).start()
        
        def on_versions_loaded(self, success):
            """Handle version list loaded"""
            self.loading = False
            self.refresh_btn.config(state="normal")
            
            if success:
                versions = vm.get_version_list()
                self.versions_list = versions
                
                # Separate releases and snapshots
                releases = [v["id"] for v in versions if v["type"] == "release"]
                snapshots = [v["id"] for v in versions if v["type"] == "snapshot"]
                
                # Add latest shortcuts
                display_list = ["latest_release", "latest_snapshot"] + releases + ["--- Snapshots ---"] + snapshots
                self.version_combo["values"] = display_list
                
                # Set default
                saved_version = config.get("version", "latest_release")
                if saved_version in display_list:
                    self.version_var.set(saved_version)
                else:
                    self.version_var.set("latest_release")
                
                self.status_var.set(f"✅ {len(releases)} releases, {len(snapshots)} snapshots loaded")
            else:
                self.status_var.set("❌ Failed to fetch versions (check internet)")
                self.version_combo["values"] = ["offline_mode"]
                self.version_var.set("offline_mode")
        
        def on_version_change(self, event=None):
            config.set("version", self.version_var.get())
        
        def update_ram_label(self, value, label):
            ram = int(float(value))
            label.config(text=f"{ram} MB")
            self.ram_var.set(str(ram))
            config.set("ram", str(ram))
        
        def launch_game(self):
            """Launch Minecraft"""
            username = self.username_var.get().strip()
            if not username:
                messagebox.showerror("Error", "Please enter a username!")
                return
            
            version_id = self.version_var.get()
            ram = int(self.ram_var.get())
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            jvm_args = self.jvm_args_var.get()
            
            # Resolve version
            if version_id == "latest_release":
                for v in self.versions_list:
                    if v["type"] == "release":
                        version_id = v["id"]
                        break
            elif version_id == "latest_snapshot":
                for v in self.versions_list:
                    if v["type"] == "snapshot":
                        version_id = v["id"]
                        break
            
            self.status_var.set(f"🚀 Launching Minecraft {version_id}...")
            self.launch_btn.config(state="disabled", text="⏳ Launching...")
            self.root.update()
            
            def launch_thread():
                try:
                    # Get version JSON
                    vjson = vm.get_version_json(version_id)
                    if not vjson:
                        self.root.after(0, lambda: self.launch_error(f"Version {version_id} not found!"))
                        return
                    
                    # Find Java
                    java_path = self.find_java(version_id)
                    if not java_path:
                        self.root.after(0, lambda: self.launch_error(
                            "Java not found!\n\nInstall Java from:\n• java.com/download\n• adoptium.net"))
                        return
                    
                    # Get launch args
                    launch_args = vm.get_java_args(version_id, username, ram, 
                                                  (width, height), jvm_args)
                    
                    if not launch_args:
                        self.root.after(0, lambda: self.launch_error("Failed to build launch arguments"))
                        return
                    
                    # Launch!
                    cmd = [java_path] + launch_args
                    
                    self.root.after(0, lambda: self.status_var.set(
                        f"▶ Running Minecraft {version_id}... Close game to return"))
                    
                    proc = subprocess.Popen(cmd, cwd=str(MINECRAFT_DIR),
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                    proc.wait()
                    
                except Exception as e:
                    self.root.after(0, lambda: self.launch_error(f"Launch failed: {str(e)}"))
                finally:
                    self.root.after(0, self.launch_reset)
            
            threading.Thread(target=launch_thread, daemon=True).start()
        
        def find_java(self, version_id):
            """Find suitable Java installation"""
            # Check configured path first
            configured = config.get("java_path", "")
            if configured and os.path.exists(configured):
                return configured
            
            # Check bundled Java
            bundled = JAVA_DIR / "bin" / "javaw.exe"
            if bundled.exists():
                return str(bundled)
            
            # Detect version requirement
            major = 8  # Default for older versions
            try:
                ver_num = version_id.split(".")[1] if "." in version_id else "8"
                if version_id.startswith("1."):
                    sub = int(version_id.split(".")[1]) if len(version_id.split(".")) > 1 else 8
                    if sub >= 18:
                        major = 17
                    elif sub >= 16:
                        major = 11
                    else:
                        major = 8
            except:
                pass
            
            # Search common Java paths
            java_paths = [
                os.environ.get("JAVA_HOME", ""),
                r"C:\Program Files\Java\jre1.8.0_341\bin\javaw.exe",
                r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
                r"C:\Program Files\Eclipse Adoptium\jdk-17.0.6.10-hotspot\bin\javaw.exe",
                r"C:\Program Files\AdoptOpenJDK\jdk-17.0.6.10-hotspot\bin\javaw.exe",
                r"C:\Program Files\Microsoft\jdk-17.0.6.10-hotspot\bin\javaw.exe",
                r"C:\Program Files\Java\jdk-21\bin\javaw.exe",
                r"C:\Program Files\Java\jdk-1.8\bin\javaw.exe",
            ]
            
            # Scan Program Files for Java
            for pf in [os.environ.get("ProgramFiles", "C:\\Program Files"), 
                      os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")]:
                if os.path.exists(pf):
                    for root_dir in os.listdir(pf):
                        if "java" in root_dir.lower() or "jdk" in root_dir.lower() or "jre" in root_dir.lower() or "adopt" in root_dir.lower() or "semeru" in root_dir.lower():
                            javaw = os.path.join(pf, root_dir, "bin", "javaw.exe")
                            if os.path.exists(javaw):
                                java_paths.append(javaw)
            
            for path in java_paths:
                if path and os.path.exists(path):
                    config.set("java_path", path)
                    return path
            
            # Last resort: try PATH
            for ext in ["", "w"]:
                try:
                    result = subprocess.run(["java" + ext, "-version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        javaw = f"java{ext}"
                        config.set("java_path", javaw)
                        return javaw
                except:
                    pass
            
            return None
        
        def launch_error(self, msg):
            messagebox.showerror("Launch Error", msg)
            self.status_var.set(f"❌ Error: {msg[:50]}...")
        
        def launch_reset(self):
            self.launch_btn.config(state="normal", text="▶  LAUNCH MINECRAFT")
            self.status_var.set("✅ Game closed. Ready to launch again.")
        
        def join_server(self):
            """Save server IP for direct connect"""
            ip = self.server_var.get().strip()
            if ip:
                config.set("server_ip", ip)
                self.status_var.set(f"✅ Server saved: {ip}")
        
        def change_skin(self):
            """Open skin changer (placeholder)"""
            messagebox.showinfo("Skin Changer", 
                               "Skin changer coming soon!\n\n"
                               "For now, use Minecraft.net\n"
                               "to change your skin.")
        
        def install_mods(self):
            """Open mods folder"""
            os.makedirs(MINECRAFT_DIR / "mods", exist_ok=True)
            os.startfile(MINECRAFT_DIR / "mods")
            self.status_var.set("📂 Opened mods folder")
        
        def install_forge(self):
            """Download and install Forge"""
            self.status_var.set("📥 Opening Forge website...")
            webbrowser.open("https://files.minecraftforge.net/net/minecraftforge/forge/")
        
        def install_fabric(self):
            """Download and install Fabric"""
            self.status_var.set("📥 Opening Fabric website...")
            webbrowser.open("https://fabricmc.net/use/installer/")
        
        def install_optifine(self):
            """Download and install OptiFine"""
            self.status_var.set("📥 Opening OptiFine website...")
            webbrowser.open("https://optifine.net/downloads")
        
        def open_minecraft_dir(self):
            """Open .minecraft folder"""
            os.makedirs(MINECRAFT_DIR, exist_ok=True)
            os.startfile(MINECRAFT_DIR)
        
        def open_github(self):
            """Open GitHub repo"""
            webbrowser.open("https://github.com/ayushrajdev9-cmyk/A2Launcher")

# ─── CLI Mode ──────────────────────────────────────────────────

def cli_mode():
    """Command-line interface mode"""
    print(f"""
╔═══════════════════════════════════════════╗
║     {LAUNCHER_NAME} - Minecraft Launcher        ║
║     by {AUTHORS}               ║
╚═══════════════════════════════════════════╝

Commands:
  launch [version]  - Launch Minecraft
  list              - List available versions
  install <version> - Download a version
  config            - Show current config
  help              - Show this help
    """)
    
    if len(sys.argv) < 2:
        print("Usage: python launcher.py <command> [args]")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        print("📋 Fetching versions...")
        if vm.fetch_manifest():
            releases = [v["id"] for v in vm.get_version_list() if v["type"] == "release"]
            snapshots = [v["id"] for v in vm.get_version_list() if v["type"] == "snapshot"]
            print(f"\n✅ Releases ({len(releases)}):")
            for v in releases[-10:]:
                print(f"  • {v}")
            print(f"\n✅ Snapshots ({len(snapshots)}):")
            for v in snapshots[-5:]:
                print(f"  • {v}")
        else:
            print("❌ Failed to fetch versions")
    
    elif cmd == "launch":
        version = sys.argv[2] if len(sys.argv) > 2 else config.get("version", "latest_release")
        username = config.get("username", "Player")
        print(f"🚀 Launching Minecraft {version} as {username}...")
        print("(GUI mode recommended - run without arguments)")
    
    elif cmd == "config":
        print("📋 Current Configuration:")
        for k, v in config.data.items():
            print(f"  {k}: {v}")
    
    else:
        print(f"Unknown command: {cmd}")

# ─── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════╗
    ║     {LAUNCHER_NAME} v{VERSION}                   ║
    ║  Minecraft Launcher by {AUTHORS}  ║
    ╚═══════════════════════════════════════════╝
    """)
    
    if TK_AVAILABLE and len(sys.argv) < 2:
        root = tk.Tk()
        app = MinecraftLauncher(root)
        root.mainloop()
    else:
        cli_mode()
