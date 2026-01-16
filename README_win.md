# Ample - Windows Port (Legacy Apple Emulator Frontend)

This is a precision port of the original macOS [Ample](https://github.com/ksherlock/ample) project to the Windows platform. Remodelled using Python and PySide6 (Qt), this project aims to achieve 100% visual parity with the original's aesthetics and minimalist workflow.

## 🌟 Core Features (Windows Exclusive Optimizations)

*   **100% macOS Visual Parity**: Redesigned top toolbar, rounded corner interface, and premium dark mode styling to deliver an authentic "boutique" experience.
*   **MAME 0.284 Compatibility**: Perfectly aligned with the latest MAME official parameters, resolving slot conflicts found in older versions.
*   **Dynamic Slot Validation (Smart Validation)**: Automatically queries supported slots and devices before launching, intelligently filtering invalid parameters to ensure a 100% launch success rate.
*   **Deep Persistence**:
    *   **Window State**: Automatically remembers the last window position, size, and sidebar proportions.
    *   **Auto-Resume**: Reopens to the last selected machine and expanded directory for a seamless experience.
*   **Powerful Video/CPU Control**:
    *   **BGFX Support**: Built-in support for CRT Geometry Deluxe, HLSL, Scanlines, and other professional rendering filters.
    *   **Performance Tuning**: Supports 100% - 500% CPU speed adjustment, Rewind functionality, and built-in Debugger toggle.
*   **ROM & MAME One-Click Deployment**:
    *   **Auto-Download**: Integrated downloader for official MAME 0.284 binaries.
    *   **Path Auto-Detection**: Detects `mame_bin` path upon startup with visual ✅ status markers.
    *   **ROM Completion**: Interfaces with support servers to automatically fetch missing BIOS or system ROMs.
*   **Pixel-Perfect Alignment (UI Perfection)**:
    *   **Mac Native Slot Controls**: Replicates Mac-style dropdown menus with right-aligned labels, blue double-arrow (↕) indicators, and gray backgrounds.
    *   **Smart Hamburger Menu**: Supports sub-slot bubble popups with intelligent toggle logic (click to open, click again to close).
    *   **Precise Layout**: All control elements, spacing, and alignment lines are pixel-aligned with the macOS version of Ample.

## 🛠️ Quick Start

1.  **Setup Environment**:
    Ensure you have Python 3.9+ installed, then run:
    ```powershell
    pip install -r requirements.txt
    ```

2.  **Run Application**:
    ```powershell
    python ample_win/main.py
    ```

3.  **Quick Deployment**:
    *   Go to **⚙️ Settings** -> click **Download MAME**.
    *   Follow prompts to extract MAME to `ample_win\mame_bin\`.
    *   Click **🎮 ROMs** and press **Download Missing ROMs** to complete system files.

4.  **Launch**:
    *   Select your desired machine from the list.
    *   **Double-click** or click **Launch MAME** in the bottom right to start.

## 📂 Project Structure

*   `main.py`: Core UI interface with persistence features (PySide6).
*   `data_manager.py`: Parses original `.plist` resource files (Model, Slot, Media definitions).
*   `mame_launcher.py`: Smartly constructs MAME command lines and handles cross-version compatibility.
*   `rom_manager.py`: Manages system files under `%APPDATA%\Ample\roms`.
*   `mame_downloader.py`: Download engine for the latest MAME (x64) binaries.

## 📝 Acknowledgments

*   Original macOS Version: [Kelvin Sherlock](https://github.com/ksherlock)
*   **Windows Port by anomixer + Antigravity**: Dedicated to bringing the ultimate Apple II / Macintosh emulation experience to the Windows ecosystem.
