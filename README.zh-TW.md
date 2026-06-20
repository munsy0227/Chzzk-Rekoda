# CHZZK Rekoda（Chzzk-Rekoda）

**語言：** [한국어](README.md) | [English](README.en.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

這是一個使用 Streamlink 和 FFmpeg 製作、支援 Windows、macOS、Linux 的 CHZZK 自動錄製程式。

它也是一個即使不熟悉電腦的人也能輕鬆使用的 **CHZZK 自動錄製程式**。  
直播開始時會自動開始錄製，直播結束後會自動儲存。

[[教學] 在 Android 手機上安裝程式](https://github.com/munsy0227/Chzzk-Rekoda/discussions/17)

[[TUTORIAL] How to Install Chzzk-Rekoda in Android Systems](https://github.com/munsy0227/Chzzk-Rekoda/discussions/18)

---

## 1. 安裝（下載）

請閱讀並按照你正在使用的作業系統（Windows、Mac、Linux）對應的說明操作。
安裝過程中出現語言選擇畫面時，請先選擇想使用的語言。

### Windows 使用者

**第 1 步：下載程式**
1. 點擊此頁面上方的綠色 **[Code]** 按鈕。
2. 在選單中點擊 **[Download ZIP]** 下載壓縮檔。
3. 解壓縮下載的檔案。（建議解壓縮到「桌面」等容易找到的位置。）

（如果你可以使用 Git，請使用 Git。）

**第 2 步：執行安裝程式**
1. 進入解壓縮後的資料夾。
2. 找到 `install.bat` 檔案並雙擊執行。
3. 黑色視窗會開啟，並自動安裝所需檔案。可能需要一些時間，請等待。
4. 安裝完成後，會自動顯示設定畫面。

---

### macOS / Linux 使用者

**第 1 步：開啟終端機**
- **Mac：** 按 `Command` + `Space`，搜尋「終端機」並執行。
- **Linux：** 執行你使用的終端機應用程式。

**第 2 步：輸入命令**
將下面的命令逐行複製到終端機中，然後按 Enter。

1. **下載程式**
   ```bash
   git clone https://github.com/munsy0227/Chzzk-Rekoda.git
   cd Chzzk-Rekoda
   ```

2. **安裝 FFmpeg（錄製必需）**
   - **Mac 使用者（需要 Homebrew）：**
     ```bash
     brew install ffmpeg
     ```
   - **Ubuntu/Debian 使用者：**
     ```bash
     sudo apt install ffmpeg -y
     ```
   - **Arch Linux 使用者：**
     ```bash
     sudo pacman -S ffmpeg uv
     ```

3. **執行安裝腳本**
   ```bash
   ./install
   ```

---

## 2. 設定（新增頻道）

必須先註冊想要錄製的實況主，錄製才會運作。  
如果安裝後設定畫面關閉了，請執行 `settings.bat`（Windows）或 `./settings`（Mac/Linux）。

1. 選單出現後，按鍵盤數字進行選擇。
   - **輸入 `1` 後按 Enter**：Channel Settings（頻道設定）
   - **輸入 `1` 後按 Enter**：Add Channel（新增頻道）

2. 輸入 **實況主唯一 ID**。
   - 它是 CHZZK 頻道地址最後面的英文字母和數字。
   - 範例：如果地址是 `https://chzzk.naver.com/abc1234`，則 `abc1234` 是 ID。

3. 輸入 **實況主名稱**。
   - 也可以使用你自己容易辨識的暱稱。

4. 輸入 **儲存路徑**。
   - 如果什麼都不輸入直接按 Enter，檔案會儲存在程式資料夾中。

5. 如果輸入的資訊正確，請輸入 `Y`。

> **提示：** 要錄製需要成人驗證的直播，需要在設定選單的 **5. Cookie Settings** 中輸入 Cookie 值（NID_AUT、NID_SES）。
> 儲存副檔名可在 **2. Recording Settings** 中從 `ts`、`mkv`、`webm` 中選擇，同一選單還可以設定是否每隔幾小時或幾分鐘分割錄製檔案。AV1 編碼可在 **4. AV1 Settings** 中啟用。遇到 DNS 問題時，可在 **6. DNS-over-HTTPS Settings** 中設定並啟用 DoH 地址。語言可在 **8. Language Settings** 中從韓語、英語、簡體中文、繁體中文、日語中選擇。

---

## 3. 開始錄製

現在只要讓程式保持執行即可。

### Windows
雙擊資料夾中的 `chzzk_record.bat` 檔案。

### Mac / Linux
在終端機中輸入以下命令。
```bash
./chzzk_record
```

如果黑色視窗開啟並顯示文字，表示正在正常運作。  
**關閉此視窗會停止錄製，請保持開啟！**（可以最小化。）

---

## 常見問題（FAQ）

**Q. 錄製的檔案在哪裡？**
A. 如果設定時沒有另外指定儲存路徑，檔案會儲存在專案資料夾中。

**Q. 如何關閉程式？**
A. 關閉正在執行的黑色視窗（終端機），或點擊該視窗後按鍵盤上的 `Ctrl` + `C`。

**Q. 發生錯誤！**
A. 請到 [Issues](https://github.com/munsy0227/Chzzk-Rekoda/issues) 描述症狀，我們可以協助你。

---

## 免責聲明及注意事項

- 本程式是根據 **MIT 授權條款** 發布的開源軟體。
- 軟體按 **「原樣（AS IS）」** 提供，因使用程式而產生的一切結果的法律責任完全由 **使用者本人** 承擔。
- **錄製的影片不得在私人用途及實況主指定範圍之外未經許可使用，影片使用的一切責任由錄製該影片的使用者承擔。**
- **上傳完整影片的行為（無論公開或非公開）均違反著作權法**，著作權人可能提起訴訟。
- 為防止 Deepfake，**作為 AI 訓練資料使用的行為也可能被禁止。**

### 著作權相關範例（라디유）
- 著作權已根據 라디유 的意願委託給 Sandbox Network。
- 作為 AI 訓練資料使用的行為同樣屬於著作權侵權。
- 除官方粉絲社群外，剪輯不能上傳到其他地方。（不限於公開或非公開）
- 即使遵守了指南，也可能根據 라디유 或 Sandbox Network 的判斷被刪除。

### 非官方專案說明
本專案及貢獻者與 **NAVER**、**CHZZK** 或其關係企業及子公司不存在任何合作、授權、批准或官方連結關係。本專案是為了提供便利而開發的獨立、非營利、非官方程式。

### 商標說明
包括「CHZZK」、「NAVER」在內的相關名稱、標誌、徽章和圖像均為相應所有者的註冊商標。這些商標僅用於識別和引用目的，不暗示與商標權人的任何關聯。本專案明確聲明無意侵犯相關商標權或對商標權人造成損害。

### 著作權和條款遵守
本專案不主張對串流影片、音訊或其他第三方內容擁有所有權，也不授予這些內容的任何授權。使用者有責任自行確認並遵守相關著作權法、平台政策（如 CHZZK 使用條款等）和當地法律。透過本專案進行儲存、複製、散布、傳輸或商業使用的責任完全由使用者承擔。
