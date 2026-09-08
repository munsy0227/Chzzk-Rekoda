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
4. When installation is complete, the settings screen opens automatically.

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

> **Tip:** To record broadcasts that require adult or membership verification, open **5. NAVER Cookie Settings** and either sign in to NAVER directly in a new Chrome, Microsoft Edge, or Firefox window to import the cookies (NID_AUT, NID_SES), or enter the values manually. The browser login method may require an internet connection to prepare a compatible driver on first use.
> The save extension can be selected from `ts`, `mkv`, or `webm` in **2. Recording Settings**, and the same menu lets you set whether recording files are split every few hours or minutes. AV1 encoding can be enabled in **4. AV1 Settings**. If you have DNS problems, set and enable a DoH URL in **6. DNS-over-HTTPS Settings**. The language can be changed in **8. Language Settings** among Korean, English, Simplified Chinese, Traditional Chinese, and Japanese.

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

On Windows, run `chzzk_gui.bat`; on macOS/Linux, run `./chzzk_gui`. Qt is installed only for the optional GUI. The `settings` and `chzzk_record` CLIs remain available.

- Use the ribbon to search by channel name or ID, add/edit/unregister channels, and change every recording setting. Hover over a setting or use F1/the help button for explanations.
- CHZZK profile images appear as channel icons when available. Failed image lookups fall back to the first character of the name.
- A **frame from the selected channel's current recording file updates every 5 seconds**. No audio is played. Insufficient data or unreadable frames show a message and retry. Disabling the preview does not stop recording.
- Stop and window close wait for the existing recorder to finish its files. A process lock prevents duplicate CLI/GUI recording within the project. Conflicting settings edits ask you to reload instead of overwriting another editor's changes.
- Saved recording options apply to new recording tasks. Restart the recorder to apply DNS and file logging changes.

A desktop display environment and FFmpeg are required. Browser login opens a new browser and imports cookies automatically. Real browser login and Windows/macOS GUI behavior still require platform-specific verification.
