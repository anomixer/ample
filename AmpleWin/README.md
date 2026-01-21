# AmpleWin - Windows Port (Legacy Apple Emulator Frontend)

[English](README.md) | [繁體中文](README_tw.md)

This is a precision port of the macOS native [Ample](https://github.com/ksherlock/ample) project to the Windows platform.

![](screenshot-v0.284.png)

> [!IMPORTANT]
> **Architecture Note**: The Windows Port codebase is **entirely rebuilt and runs independently** using Python and PySide6 (Qt). It is completely separated from the original macOS version (Objective-C) at the code level. No modifications were made to the macOS source code; only the essential machine definition resources (.plist) are shared.

## ⚔️ Ample (macOS) vs. AmpleWin (Windows) Comparison

| Feature | Ample (macOS Native) | AmpleWin (Windows Optimized) | Optimization & Notes |
| :--- | :--- | :--- | :--- |
| **Language** | Objective-C (Cocoa) | **Python 3.11 + PySide6 (Qt)** | Independent development, **zero changes to Mac source code** |
| **Installation** | .dmg Image / Homebrew | **Portable (+ .bat Auto-Config)** | One-click setup for Python and dependencies via `AmpleWin.bat` |
| **UI** | Native macOS Components | **1:1 Pixel-Perfect QSS Replica** | Replicates Mac aesthetic, with **Adaptive Light/Dark Theme** support |
| **MAME Integration** | Built-in Custom Core or Self-selected | **Official Core Download or Self-selected** | Users can update MAME independently or download via app |
| **Machine Selection** | Supports Default Bookmark | **Full Session Persistence (Auto-Load)** | Auto-loads last used machine state without manual bookmarking |
| **Software List Perf** | Synchronous Loading (Full XML) | **Deferred Loading** | **Major Optimization**: Instant machine switching, loads on search |
| **Software Search UI** | Standard Pop-up List | **Smart Overlay Search** | Supports real-time search and full descriptive names without UI shifts |
| **ROM Download** | Supports Auto-Download | **Multi-threaded Acceleration** | High-speed parallel downloading for missing system ROMs |
| **Validation** | Relies on Static .plist | **Live Parameter Validation** | **Major Optimization**: Validates against MAME to prevent launch crashes |
| **Video Support** | Metal / OpenGL / BGFX | **BGFX / OpenGL / Vulkan / D3D11 / D3D12** | Optimized for Windows with multi-generational DirectX support |
| **Networking** | Apple VMNet Framework | **Npcap (WinPcap) / PCAP** | Standard networking via Npcap (no root fix needed) |
| **Operating Logic** | Sticky Software Selection | **Sticky Software Selection** | Preserves compatible software selection when switching machines |

## 🌟 Key Features

### 🍏 Faithful Mac Experience (Feature Parity)
*   **Visual Precision**: 
    *   **Resolution Scaling**: Precision support for **Window 1x-4x** modes with machine-specific aspect ratio heuristics (e.g., Apple II 4:3 correction).
    *   **Square Pixels**: Specialized integer-scaling mode (e.g., 1120x768) to eliminate pixel shimmering.
*   **Software Library**:
    *   **Smart Filtering**: Automatically identifies supported media types (flop1, flop2, cass...) to match machine capabilities.
    *   **Search Overlay**: Integrated Mac-style search with auto-completion and full descriptive names.
*   **Shared Directory**: Full parity with the Mac version, allowing direct host-to-emulator file sharing via the `-share_directory` argument.
*   **VGM Support (Advanced)**: Since modern MAME removed VGM support, AmpleWin implements a robust background workflow to download and configure the **MAME-VGM Mod (v0.280)**. It uses a non-destructive extraction process (`mame-vgm.exe`) to preserve your main MAME core while restoring high-fidelity music recording.

### 🪟 Windows-Specific Optimizations
*   **Performance**:
    *   **Concurrent Downloading**: Multi-threaded system for high-speed ROM acquisition.
    *   **Clean Workspace**: All MAME side-car files (nvram, cfg, sta) are strictly isolated within the `mame_bin` directory.
    *   **Deferred XML Loading**: Major optimization for instant machine switching and search response.
*   **UI Enhancements**:
    *   **Adaptive Theme**: Real-time synchronization with Windows Light/Dark system theme.
    *   **Command Preview**: Real-time 4-line console preview to monitor exactly what parameters are being passed to MAME.
*   **Flexible Backend**: Full support for BGFX, OpenGL, Vulkan, and **DirectX 11/12** out of the box.

## 🛠️ Quick Start

1.  **Launch Ample**:
    Enter the **`AmpleWin`** folder and run **`AmpleWin.bat`**.
    *   The script will check the Python environment, install dependencies, and start the app.
2.  **Fast Deployment**:
    *   Go to **⚙️ Settings** -> Click **Download MAME** to auto-configure the emulator.
    *   Click **🎮 ROMs** to download system firmware.
    *   Click **📂 Ample Dir** to quickly open the local application folder.
3.  **Start playing**:
    *   Select a machine from the left panel.
    *   **Double-click** the machine name or click **Launch MAME** to start.

## 🌐 Networking (Advanced)

To simulate networking hardware like **Uthernet II**, Windows requires [Npcap](https://nmap.org/npcap/) (install in "WinPcap compatible mode"). Unlike the macOS version, no "Fix Permissions" is required as Windows handles hardware access via drivers.

## 📂 Project Structure

*   `main.py`: Core UI and logic, handles rendering and settings persistence.
*   `data_manager.py`: Parses `.plist` resources and MAME `.xml` software lists.
*   `mame_launcher.py`: Crucial component for dynamic slot validation and command construction.
*   `rom_manager.py`: Manages system files under `mame_bin\roms`.
*   `mame_downloader.py`: Automatic engine for downloading and extracting MAME.

## 📝 Acknowledgments

*   Original macOS version developer: [Kelvin Sherlock](https://github.com/ksherlock)
*   **Windows Port Developers: anomixer + Antigravity**: Dedicated to providing the ultimate Apple II / Macintosh emulation experience on Windows.
