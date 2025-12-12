# 🚀 Quick Start Guide - Valheim Mod Manager

Get up and running with Valheim Mod Manager in 5 minutes!

## 📥 Installation (2 minutes)

### Option 1: Use Pre-built Executable (Recommended)
1. Download latest release from [Releases](https://github.com/yourusername/valheim-mod-manager/releases)
2. Extract ZIP file
3. Run `ValheimModManager.exe` (Windows) or `ValheimModManager` (Linux/Mac)

### Option 2: Run from Source
```bash
# Clone repository
git clone https://github.com/yourusername/valheim-mod-manager.git
cd valheim-mod-manager

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## ⚡ First-Time Setup (2 minutes)

### 1. Set Game Path
When you first launch, the app will try to auto-detect your Valheim installation.

If it doesn't find it:
1. Click **Settings** tab
2. Click **Browse** next to "Game Path"
3. Navigate to your Valheim folder:
   - **Windows**: Usually `C:\Program Files (x86)\Steam\steamapps\common\Valheim`
   - **Linux**: Usually `~/.steam/steam/steamapps/common/Valheim`
4. Click **Save**

### 2. Create Your First Profile
1. Go to **Profiles** tab
2. Click **➕ New Profile**
3. Enter a name (e.g., "Quality of Life")
4. Click **Create**

## 🎮 Using the Mod Manager (1 minute)

### Download and Install Mods

1. **Browse Mods**
   - Go to **Browse Mods** tab
   - Search for "Valheim Plus" (popular mod)
   - Click on it to see details
   - Click **📥 Download**

2. **Add to Profile**
   - Go to **Profiles** tab
   - Your new profile should be selected
   - Click **➕ Add Mods**
   - Find "Valheim Plus" in the list
   - Check the box next to it
   - Click **OK**

3. **Launch Game**
   - Make sure your profile is selected in the dropdown (top toolbar)
   - Click **🚀 Launch Game**
   - The mod manager will deploy your mods and start Valheim!

## 🎯 Recommended First Mods

Here are some popular, stable mods to start with:

1. **BepInExPack** (Required for most mods)
   - Modding framework
   - Downloads: 2M+
   - ⭐⭐⭐⭐⭐

2. **ValheimPlus**
   - Quality of life improvements
   - Configurable gameplay tweaks
   - Downloads: 1.5M+
   - ⭐⭐⭐⭐⭐

3. **Epic Loot**
   - Diablo-style loot system
   - Magic items and crafting
   - Downloads: 500K+
   - ⭐⭐⭐⭐⭐

4. **Build Camera**
   - Free camera for building
   - Easier construction
   - Downloads: 300K+
   - ⭐⭐⭐⭐

## 💡 Pro Tips

### Multiple Profiles
Create different profiles for different playstyles:
- **Vanilla+**: Just quality of life mods
- **Hardcore**: Difficulty mods
- **Creative**: Building and exploration mods
- **Multiplayer**: Compatible mods for server play

### Managing Configs
Many mods have configuration files:
1. Go to **Configs** tab
2. Select your profile and mod
3. Edit settings (e.g., increase inventory size)
4. Click **Save**
5. Changes apply on next launch

### Updating Mods
1. Tools → **Check for Updates**
2. See which mods have updates
3. Download new versions
4. Replace old version in your profile

### Troubleshooting
If game won't start:
1. Check **Help → View Logs**
2. Look for errors
3. Common issues:
   - Missing BepInEx (download it first)
   - Conflicting mods (disable one)
   - Outdated mods (update them)

## 🔧 Common Workflows

### Creating a "Clean" Vanilla Profile
```
1. Profiles → New Profile → "Vanilla"
2. Don't add any mods
3. Use this when you want pure Valheim
```

### Installing a Full Modpack
```
1. Browse for modpack on Thunderstore
2. Note all required mods
3. Download each mod
4. Add all to a new profile
5. Dependencies auto-resolve!
```

### Switching Between Modded/Unmodded
```
1. Create "Vanilla" and "Modded" profiles
2. Use dropdown to switch
3. Click Launch - mods deploy automatically
4. No manual file copying needed!
```

## ❓ FAQ

**Q: Will this work with my existing saves?**
A: Yes! Mods don't affect save files. You can switch between modded and vanilla anytime.

**Q: Can I use this on a server?**
A: Client-side yes, but server mods need to be installed on the server too.

**Q: How do I uninstall?**
A: Just delete the mod manager folder. It doesn't touch your Valheim installation except during deployment.

**Q: Is this safe?**
A: Yes! The mod manager only copies files when you launch. It creates backups before deployment.

**Q: Why isn't my mod working?**
A: Check:
1. BepInEx is installed
2. Mod is enabled in profile
3. No conflicting mods
4. Mod is updated for your Valheim version

## 📚 Next Steps

Now that you're set up:

1. **Explore Mods**: Browse tab has 1000+ mods
2. **Customize Configs**: Fine-tune mod settings
3. **Create Profiles**: Different configs for different moods
4. **Join Community**: Share profiles, get help

## 🆘 Need Help?

- **Issues**: [GitHub Issues](https://github.com/yourusername/valheim-mod-manager/issues)
- **Wiki**: [Full Documentation](https://github.com/yourusername/valheim-mod-manager/wiki)
- **Discord**: [Community Server](https://discord.gg/example)

---

**Enjoy your modded Valheim experience! 🎮⚔️🏰**
