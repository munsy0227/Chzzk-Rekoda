# Chzzk-Rekoda

**Languages:** [한국어](README.md) | [English](README.en.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

Chzzk-Rekoda is an automatic CHZZK recording program for Windows, macOS, and Linux, built with Streamlink and FFmpeg.

It is also a **CHZZK automatic recording program** designed to be easy to use even for people who are not familiar with computers.  
When a broadcast starts, it automatically begins recording, and when the broadcast ends, it saves the recording by itself.

[[Tutorial] Install the program on an Android phone](https://github.com/munsy0227/Chzzk-Rekoda/discussions/17)

[[TUTORIAL] How to Install Chzzk-Rekoda in Android Systems](https://github.com/munsy0227/Chzzk-Rekoda/discussions/18)

---

## 1. Installation (Download)

Read and follow the instructions for your operating system: Windows, Mac, or Linux.
When the language selection screen appears during installation, choose the language you want first.

### Windows Users

**Step 1: Download the program**
1. Click the green **[Code]** button near the top of this page.
2. Click **[Download ZIP]** in the menu to download the compressed file.
3. Extract the downloaded file. A location that is easy to find, such as the Desktop, is recommended.

(If you can use Git, use Git.)

**Step 2: Run the installer**
1. Open the extracted folder.
2. Find `install.bat` and double-click it.
3. A black window will open and automatically install the required files. This can take some time, so please wait.
4. Choose **GUI / CLI** at the end of installation. GUI finishes installation and opens the app; CLI starts the terminal settings menu.

---

### macOS / Linux Users

**Step 1: Open a terminal**
- **Mac:** Press `Command` + `Space`, search for "Terminal", and run it.
- **Linux:** Run the terminal app you use.

**Step 2: Enter commands**
Copy the following commands one line at a time into the terminal and press Enter.

1. **Download the program**
   ```bash
   git clone https://github.com/munsy0227/Chzzk-Rekoda.git
   cd Chzzk-Rekoda
   ```

2. **Install FFmpeg (required for recording)**
   - **Mac users (Homebrew required):**
     ```bash
     brew install ffmpeg
     ```
   - **Ubuntu/Debian users:**
     ```bash
     sudo apt install ffmpeg -y
     ```
   - **Arch Linux users:**
     ```bash
     sudo pacman -S ffmpeg uv
     ```

3. **Run the install script**
   ```bash
   ./install
   ```

---

## 2. Settings (Add Channels)

You must register the streamer you want to record before recording can work.  
If the settings screen closed after installation, run `settings.bat` on Windows or `./settings` on Mac/Linux.

1. When the menu appears, press a number on the keyboard to choose an item.
   - **Enter `1` and press Enter**: Channel Settings
   - **Enter `1` and press Enter**: Add Channel

2. Choose how to **add a channel**.
   - **Search by channel name**: enter a search term, then select a channel from results that show both its name and ID.
   - **Add directly by channel ID**: enter the ID at the end of the CHZZK channel URL, and the official channel name is retrieved automatically.

3. Verify the **channel name and ID** that were found.
   - An already registered ID is marked in the search results and cannot be added twice.
   - If another registered ID has the same name, its existing ID is shown so you can distinguish channels with identical names.

4. Enter the **save path**.
   - If you press Enter without typing anything, a folder named after the official channel is created inside the project and recordings are saved there.
   - You can enter another folder name or path when needed.

5. If the displayed channel name, ID, and save path are correct, enter `Y`.

> **Tip:** To record broadcasts that require adult or membership verification, open **4. NAVER login** and either sign in to NAVER directly in a new Chrome, Microsoft Edge, or Firefox window to import the cookies (NID_AUT, NID_SES), or enter the values manually. The browser login method may require an internet connection to prepare a compatible driver on first use.
> Use **2. Recording and quality** for format, splitting, resolution and FPS; **3. Encoding** for H.264/HEVC/AV1; **5. Network** for DoH; and **6. Language and logs** for language and file logging. Per-channel overrides are under **1. Channels → 4. Channel split and quality**. `0` goes back or exits.

---

## 3. Start Recording

Now you only need to leave the program running.

### Windows
Double-click `chzzk_record.bat` in the folder.

### Mac / Linux
Enter the following command in the terminal.
```bash
./chzzk_record
```

If a black window is open and text is appearing, it is working normally.  
**If you close this window, recording stops, so keep it open!** You may minimize it.

---

## FAQ

**Q. Where are the recorded files?**
A. If you did not set a separate save path, recordings are saved in the official channel-name folder inside the project.

**Q. How do I turn off the program?**
A. Close the running black window (terminal), or click the window and press `Ctrl` + `C` on the keyboard.

**Q. An error occurs!**
A. Go to [Issues](https://github.com/munsy0227/Chzzk-Rekoda/issues) and describe the problem so we can help.

---

## Disclaimer and Notes

- This program is open-source software distributed under the **MIT License**.
- The software is provided **"AS IS"**, and all legal responsibility for any results caused by using the program belongs solely to **the user**.
- **Recorded videos may not be used without permission outside private use and the scope designated by the streamer, and all responsibility for video use belongs to the user who recorded them.**
- **Uploading an entire video, whether public or private, violates copyright law**, and the copyright holder may file a lawsuit.
- To prevent deepfakes, **use as AI training material may also be prohibited.**

### Copyright Example (라디유)
- Copyright has been delegated to Sandbox Network by 라디유's decision.
- Use as AI training material is also copyright infringement.
- Clips may not be uploaded anywhere except the official fan community. This is not limited by whether the upload is public or private.
- Even if the guidelines are followed, the content may be removed at the judgment of 라디유 or Sandbox Network.

### Unofficial Project Notice
This project and its contributors have no affiliation, authorization, approval, or official connection with **NAVER**, **CHZZK**, or their affiliates or subsidiaries. This project is an independent, nonprofit, unofficial program developed for convenience.

### Trademark Notice
Names including "CHZZK" and "NAVER", as well as related names, marks, emblems, and images, are registered trademarks of their respective owners. These trademarks are used only for identification and reference purposes and do not imply any relationship with the trademark holders. This project explicitly states that it has no intention to infringe trademarks or harm trademark owners.

### Copyright and Terms Compliance
This project does not claim ownership of streaming video, audio, or other third-party content, nor does it grant any license for such content. Users are responsible for checking and complying with applicable copyright laws, platform policies such as the CHZZK Terms of Service, and local laws. Responsibility for storage, reproduction, distribution, transmission, or commercial use through this project belongs solely to the user.

## Qt ribbon GUI

The GUI shares the existing CLI's `config.json`.

```bash
uv run --extra gui chzzk_gui.py
```

On Windows, double-click **`chzzk_gui.vbs`** to launch without a CMD window. `chzzk_gui.bat` also calls this launcher. On macOS/Linux, use `./chzzk_gui`. Qt is installed only when choosing GUI.

The first GUI launch shows a wizard for language, channel search and storage folders. Finish saves your settings; you may add channels later. Reopen it from **Help → Getting started**.

- Use the ribbon to search by channel name or ID, add/edit/unregister channels, and change every recording setting. Hover over a setting or use F1/the help button for explanations.
- CHZZK profile images appear as channel icons when available. Failed image lookups fall back to the first character of the name.
- A **frame from the selected channel's current recording file updates every 5 seconds**. No audio is played. Insufficient data or unreadable frames show a message and retry. Disabling the preview does not stop recording.
- Closing the window keeps recording in the system tray by default. Use its icon to restore the window or **quit**. Disable this behavior in app settings; without a tray, closing quits. Duplicate CLI/GUI recording and conflicting settings writes are prevented.
- Saved recording options apply to new recording tasks. Restart the recorder to apply DNS and file logging changes.

The GUI requires a desktop environment and FFmpeg. **Open login window** starts the CLI browser-login procedure directly. Log in using the browser, then press Enter in the separate CLI window to return cookies to the GUI. Use **Save settings** to apply them. The GUI has no CMD window; a separate console opens only for login.

- The original broadcast title appears between channel name and status. Right-click a channel for settings, removal, storage folder and automatic recording activation.
- Split intervals and quality can inherit global defaults or be set per channel. Turning splitting off for one channel saves it in one file.
- Available `144p`, `360p`, `480p`, `720p60` and `1080p60` streams are downloaded directly. Other resolutions require encoding; FPS-only changes use a stream with the same resolution. Conversion uses the selected codec, or H.264 by default (VP9 for WebM). Missing qualities use the nearest higher rendition or best available and convert it.
- H.264 supports libx264/NVENC/QSV/AMF/VAAPI/VideoToolbox, mutually exclusive with HEVC and AV1. Hardware failures try libx264. H.264 with WebM saves as MKV.
- A UTF-8 `.txt` sidecar preserves the original title only when a long filename is shortened and hashed. This applies to individual videos and split segments. Short titles do not produce TXT files.
- The GUI uses `font/02_NotoSansCJK-TTF-VF/Variable/TTF/Subset/NotoSansKR-VF.ttf`. Only the required Korean font and the distribution’s `LICENSE` are retained.
