# AmpleWin - Windows Port (Legacy Apple Emulator Frontend)

[English](README.md) | [繁體中文](README_tw.md)

這是一個將 macOS 原生 [Ample](https://github.com/ksherlock/ample) 專案精準移植至 Windows 平台的版本。

![](screenshot-v0.284.png)

> [!IMPORTANT]
> **架構說明**：Windows Port 的程式碼是基於 Python 與 PySide6 (Qt) **完全重新開發且獨立運行**的。它與原始 macOS 版本（Objective-C）在程式碼層級上完全分開，開發過程中**未修改任何 macOS 版本的原始碼**，僅共享了最重要的機器定義資源（.plist）。

## ⚔️ Ample (macOS) vs. AmpleWin (Windows) 完整對照表

| 功能項目 | Ample (macOS 原生版) | AmpleWin (Windows 優化版) | 優化重點與說明 |
| :--- | :--- | :--- | :--- |
| **程式語言** | Objective-C (Cocoa) | **Python 3.11 + PySide6 (Qt)** | 獨立開發，**完全沒動到 Mac 版原始碼** |
| **安裝方式** | .dmg 映像檔 / Homebrew | **免安裝綠色版 (+ .bat 自動配置)** | 透過 `AmpleWin.bat` 一鍵搞定 Python 與依賴 |
| **UI 介面** | macOS 原生組件 | **1:1 像素級 QSS 複刻** | 在 Windows 實現 **Adaptive 自適應淺色/深色主題** |
| **MAME 整合** | 內建客製版核心，或自選客製版本 | **額外下載官方版核心，或自選客製版本** | 使用者可隨時更新 MAME 核心，若無亦可選擇額外下載 |
| **初始機器選擇** | 支援預設書籤 (需手動設定) | **全自動持久化 (自動載入上次狀態)** | Mac 版需設為預設書籤，Windows 版則全自動開啟 |
| **軟體清單效能** | 同步加載 (解析完整 XML) | **延遲遞增加載 (Deferred Loading)** | **重大優化**：切換機器秒開，搜尋才加載，效能更佳 |
| **軟體搜尋 UI** | 標準列表 (Pop-up) | **智慧搜尋疊層 (Smart Overlay)** | 支援即時搜尋、全名顯示，且不推擠其他 UI 元素 |
| **ROM 下載** | 支援自動下載 (補齊缺失) | **支援自動下載 (多線程加速)** | 兩平台均可補齊韌體，Windows 版採並行下載更迅速 |
| **參數驗證** | 依賴 .plist 靜態定義 | **動態查詢驗證 (Live Validation)** | **重大優化**：自動與 MAME 比對，防止指令報錯崩潰 |
| **Video 支援** | Metal / OpenGL / BGFX | **BGFX / OpenGL / Vulkan / D3D11 / D3D12** | 針對 Windows 環境最佳化，支援多代 DirectX 核心 |
| **網路連線** | Apple VMNet Framework | **Npcap (WinPcap) / PCAP** | 使用標準 Npcap 即可上網 (無須權限修復) |
| **操作邏輯** | 支援黏性軟體選取 | **支援黏性軟體選取 (Sticky Selection)** | 兩平台皆支援切換機型後保留相容的軟體選取 |

## 🌟 核心功能與 Windows 專屬優化

*   **軟體清單 (The Ultimate Library)**：
    *   **深度解析**：直接解析 MAME 的 `hash/*.xml` 清單，不依賴第三方資料庫。
    *   **Mac 風格發現**：整合搜尋框，支援「自動補完」與**完整描述性名稱顯示**。
    *   **智慧過濾**：自動識別機器支援的媒體類型 (flop1, flop2, cass...)，避免啟動參數錯誤。
*   **效能與環境優化**：
    *   **高併發下載**：多線程下載系統，可同時下載所有缺失的 ROM 檔案，大幅降低初始配置時間。
    *   **零雜訊 Workspace**：所有的 MAME 產出紀錄 (nvram, cfg, sta) 嚴格限制在 `mame_bin` 內，保持資料夾整潔。
*   **極致像素對齊 (UI Perfection)**：
    *   **🍎 經典蘋果圖示按鈕**：精確複刻原始 Mac 版的啟動觸發器。
    *   **全寬底欄主控台**：模擬 Mac 狀態欄風格，提供加大版 (4行) 即時 MAME 命令列預覽。
    *   **自適應主題切換**：與 Windows 系統主題即時同步，確保所有對話框與標籤在不同模式下均清晰可見。

## 🛠️ 快速開始

1.  **啟動 Ample**：
    進入 **`AmpleWin`** 資料夾，執行 **`AmpleWin.bat`**。
    *   腳本會自動檢查 Python 環境、安裝依賴套件並啟動程式。
2.  **快速部署**：
    *   前往 **⚙️ Settings** -> 點擊 **Download MAME** 以自動配置模擬器。
    *   點擊主介面的 **🎮 ROMs** 以補齊系統韌體。
    *   點擊 **📂 Ample Dir** 可快速開啟程式安裝目錄。
3.  **開始體驗**：
    *   從左側列表中選擇想要的機器。
    *   **雙擊** 機器名稱或點擊右下角的 **Launch MAME** 即可啟動。

## 🌐 網路功能 (進階項目)

若要在模擬器中使用 **Uthernet II** 等網路卡硬體，在 Windows 環境下需要安裝 [Npcap](https://nmap.org/npcap/) (安裝時請勾選 "WinPcap compatible mode")。與 macOS 版本不同，Windows 是透過網卡驅動程式處理硬體存取，因此不需要額外的「權限修復 (Fix Permissions)」程序。

## 📂 專案結構

*   `main.py`：核心 UI 與邏輯，負責介面算繪與持久化設定。
*   `data_manager.py`：解析 `.plist` 資源檔與 MAME 的 `.xml` 軟體清單。
*   `mame_launcher.py`：關鍵組件，負責動態驗證機器插槽並建構最優化的命令列參數。
*   `rom_manager.py`：管理 `mame_bin\roms` 下的系統檔案。
*   `mame_downloader.py`：全自動 MAME 主程式下載與解壓引擎。

## 📝 致謝

*   原始 macOS 版本開發者: [Kelvin Sherlock](https://github.com/ksherlock)
*   **Windows Port 開發者: anomixer + Antigravity**：致力於在 Windows 生態系中提供最極致的 Apple II / Macintosh 模擬體驗。
