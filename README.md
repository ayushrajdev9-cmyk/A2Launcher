# ⛏️ A2Launcher - Minecraft Launcher

**Created by: [Ayush Rajdev](https://github.com/ayushanzarai) & [Anzar Iqbal](https://github.com/ayushanzarai)**  
**GitHub:** [A2Launcher](https://github.com/ayushrajdev9-cmyk/A2Launcher)

---

## 🎯 About

**A2Launcher** is a custom **Minecraft Launcher** built from scratch in Python — inspired by TLauncher, SKLauncher, and TL Legacy. It allows you to download, manage, and launch any Minecraft version with full control over RAM, resolution, JVM arguments, and mod loaders.

Built with ❤️ by **Ayush Rajdev** and **Anzar Iqbal** for the Minecraft community.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| ✅ **Version Manager** | Fetch & launch any Minecraft version (release & snapshot) |
| ✅ **Offline Mode** | Play without a Microsoft/Mojang account |
| ✅ **RAM Control** | Allocate custom RAM (512MB – 16GB) |
| ✅ **Custom Resolution** | Set any window size (default: 854×480) |
| ✅ **JVM Arguments** | Advanced JVM tuning for performance |
| ✅ **Direct Connect** | Save server IPs for quick joining |
| ✅ **Mod Loaders** | Quick links to Forge, Fabric, OptiFine |
| ✅ **Skin Changer** | Built-in skin manager (coming soon) |
| ✅ **Auto Java Detection** | Finds Java 8, 11, 17, 21 automatically |
| ✅ **Dark Theme** | Clean, modern dark UI |
| ✅ **Open Source** | 100% free, no ads, no spyware |

---

## 📦 Installation

### Prerequisites
- **Python 3.8+** ([python.org](https://python.org))
- **Java 8, 17, or 21** ([adoptium.net](https://adoptium.net))
- Internet connection (for version downloads)

### Setup
```bash
# Clone the repository
git clone https://github.com/ayushrajdev9-cmyk/A2Launcher.git
cd A2Launcher

# Install dependencies
pip install requests

# Launch the launcher
python launcher.py
```

---

## 🎮 Usage

### GUI Mode (Recommended)
```bash
python launcher.py
```
Opens the full graphical launcher with all controls.

### CLI Mode
```bash
# List available Minecraft versions
python launcher.py list

# Launch a specific version
python launcher.py launch 1.20.4

# Show configuration
python launcher.py config
```

---

## 🖥️ Screenshots

```
╔═══════════════════════════════════════════╗
║     ⛏️ A2Launcher v1.0.0                    ║
║     by Ayush Rajdev & Anzar Iqbal          ║
╠═══════════════════════════════════════════╣
║  👤 Username: [____________]              ║
║  📦 Version: [1.20.4 ▼]       [🔄]       ║
║  💾 RAM: [████████░░░░] 2048 MB           ║
║  🖥️ Resolution: W:[854] H:[480]           ║
║  ⚙️ JVM Args: [________________]           ║
║                                           ║
║  [▶ LAUNCH MINECRAFT]  [📂 Open Folder]   ║
╚═══════════════════════════════════════════╝
```

---

## 🔧 How It Works

1. **Fetches version manifest** from Mojang's API
2. **Downloads version metadata** (libraries, assets, natives)
3. **Resolves Java version** required for the selected Minecraft version
4. **Builds classpath** with all required libraries
5. **Launches Minecraft** with proper JVM arguments

---

## 🆚 Compared to TLauncher

| Feature | A2Launcher | TLauncher |
|---------|-----------|-----------|
| Open Source | ✅ Yes | ❌ No |
| Free | ✅ Yes | ✅ Yes (with ads) |
| Offline Mode | ✅ Yes | ✅ Yes |
| Mod Loaders | ✅ Forge/Fabric/OptiFine | ✅ More options |
| Skins | 🔄 Coming soon | ✅ Yes |
| Accounts | 🔄 Coming soon | ✅ Premium |
| Updates | ✅ Active development | ✅ Regular |
| Ads | 🚫 None | ⚠️ Has ads |

---

## 🤝 Credits

### Developers
- **Ayush Rajdev** — Lead Developer, UI Design, Version Manager
- **Anzar Iqbal** — Co-Developer, Testing, Documentation

### Special Thanks
- Mojang Studios for Minecraft
- The open source Python community

---

## 📜 License

This project is **open source** and free to use, modify, and distribute.  
Minecraft is a trademark of Mojang Studios. This project is not affiliated with Mojang.

---

## ⭐ Support

If you like this launcher, please **star** the repository on GitHub!  
[⭐ Star on GitHub](https://github.com/ayushrajdev9-cmyk/A2Launcher)

---

**Made with ❤️ by Ayush Rajdev & Anzar Iqbal — India 🇮🇳**
