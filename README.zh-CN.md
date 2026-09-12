<table>
  <tr>
    <td width="58%" align="center">
      <a href="assets/screenshots/gui-recording.jpg"><img src="assets/screenshots/gui-recording.jpg" alt="GUI · 功能区操作与录制预览" width="100%"></a>
      <br><strong>GUI · 功能区操作与录制预览</strong>
    </td>
    <td width="42%" align="center">
      <a href="assets/screenshots/cli-recording.jpg"><img src="assets/screenshots/cli-recording.jpg" alt="CLI · 在终端查看录制状态" width="100%"></a>
      <br><strong>CLI · 在终端查看录制状态</strong>
    </td>
  </tr>
</table>

<p align="center"><sub>点击图片可查看原图。</sub></p>

# CHZZK Rekoda（Chzzk-Rekoda）

**语言：** [한국어](README.md) | [English](README.en.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

这是一个使用 Streamlink 和 FFmpeg 制作的 CHZZK 自动录制程序，支持 Windows、macOS 和 Linux。

它也是一个即使不熟悉电脑的人也能轻松使用的 **CHZZK 自动录制程序**。  
直播开始时会自动开始录制，直播结束后会自动保存。

欢迎通过 [Pull Request](https://github.com/munsy0227/Chzzk-Rekoda/pulls) 参与各种贡献，包括新增功能、修复错误、改进性能和完善文档。

[[教程] 在 Android 手机上安装程序](https://github.com/munsy0227/Chzzk-Rekoda/discussions/17)

[[TUTORIAL] How to Install Chzzk-Rekoda in Android Systems](https://github.com/munsy0227/Chzzk-Rekoda/discussions/18)

**[GUI 入门](#gui) · [安装指南](#installation) · [使用 CLI](#cli) · [常见问题](#faq)**

---

<a id="gui"></a>

## 1. 从 GUI 开始

GUI 与现有 CLI 共用 `config.json`。

1. 按照[下方安装指南](#installation)安装，在最后的选择界面选择 **1. GUI**。安装完成后会打开应用。
2. 首次启动 GUI 会显示语言、频道搜索和保存文件夹向导，点击完成才保存设置，也可以稍后添加频道。从 **帮助 → 初始设置** 可重新打开。
3. 选择 **主页 → 开始自动录制**。程序会等待已启用频道开播，然后开始录制。以后可通过 **添加频道** 添加更多频道。

### 下次如何打开 GUI

| 系统 | 启动方式 |
| --- | --- |
| Windows | 双击 `chzzk_gui.vbs` · 不显示 CMD 窗口（`chzzk_gui.bat` 使用同一启动器） |
| Linux | 双击 `Chzzk-Rekoda.desktop` · 如有提示，请允许执行 |
| macOS | 在安装文件夹的终端中运行 `./chzzk_gui` |

macOS/Linux 也可使用 `./chzzk_gui`。如需为现有 CLI 安装添加 GUI，或直接通过 uv 启动，请运行以下命令。只有 GUI 需要 Qt。

```bash
uv run --extra gui chzzk_gui.py
```

### 在功能区中调整设置

| 操作 | 菜单 |
| --- | --- |
| 文件格式与分割间隔 | **录制设置 → 基本录制** |
| 分辨率与 FPS | **录制设置 → 画质** |
| H.264 · HEVC · AV1 编码 | **录制设置 → H.264 / HEVC / AV1** |
| 频道独立文件夹、分割与画质 | **右键频道 → 编辑频道** |
| 导入登录 Cookie | **录制设置 → NAVER 登录** |
| 语言、日志与后台行为 | **录制设置 → 应用 · 后台** |
| 完成文件处理后退出 | **录制设置 → 完全退出程序** |

点击 **保存设置** 应用更改。将指针停留在选项上，或使用帮助按钮/F1 查看说明。

### 需要 NAVER 登录的直播

GUI 需要桌面环境和 FFmpeg。**打开登录窗口**直接启动 CLI 的浏览器登录流程。在浏览器登录后，在独立 CLI 窗口按 Enter，将 Cookie 传回 GUI，再点击 **保存设置** 应用。GUI 本身不显示 CMD 窗口，仅登录时打开独立 CLI 窗口。

<details>
<summary>展开查看画质、编码、预览和托盘等详细功能</summary>

- 通过功能区按频道名称或 ID 搜索、添加、编辑、取消注册，并调整全部录制设置。悬停设置或使用 F1/帮助按钮查看说明。
- 频道图标优先使用 CHZZK 头像，查询失败时显示名称首字。
- **每 5 秒更新所选频道当前录制文件中的一帧画面**，不播放声音。数据不足或无法读取时显示提示并重试。关闭预览不会停止录制。
- 默认关闭窗口后继续在系统托盘录制，可通过图标恢复窗口或**退出**。应用设置中可关闭此行为；无托盘时关闭窗口会退出。防止 CLI/GUI 重复录制及设置覆盖冲突。
- 保存的录制选项应用于新的录制任务。DNS 和文件日志更改需停止并重新启动录制器。

- 频道名称和状态之间显示原始直播标题。右键频道可设置、取消注册、打开保存文件夹或启停自动录制。
- 分割间隔和画质可使用全局默认值或按频道设置。关闭某频道的分割后，该频道保存为单个文件。
- 直接接收实际提供的 `144p`、`360p`、`480p`、`720p60`、`1080p60`。其他分辨率需要编码，仅改变 FPS 时使用相同分辨率的流。转换使用所选编码，未选时使用 H.264（WebM 为 VP9）。不提供的画质从最接近的更高画质或最佳画质转换。
- H.264 支持 libx264/NVENC/QSV/AMF/VAAPI/VideoToolbox，与 HEVC、AV1 只能启用一个。硬件失败时尝试 libx264。H.264+WebM 保存为 MKV。
- 仅当文件名过长而缩短并添加哈希时，在视频或各分段旁生成保留原始标题的 UTF-8 `.txt`。短标题不生成 TXT。
- GUI 使用 `font/02_NotoSansCJK-TTF-VF/Variable/OTC/NotoSansCJK-VF.ttf.ttc`，按语言选择 KR/JP/SC/TC 字体。Windows 使用 DirectWrite 和各显示器的 DPI，字体目录附带 `LICENSE`。
- **录制设置 → 完全退出程序**会等待录制文件处理完成后退出程序及托盘。分割录制容量为当前录制生成的所有分段文件实际大小之和。
- GUI 录制停止时，日志会区分停止命令、程序退出和通信连接故障等原因。启用文件日志后，也可在配置文件旁的 `log.log` 中查看。
- 窗口、任务栏和托盘使用同一程序图标。Windows 运行 `chzzk_gui.vbs` 后，会在安装文件夹中生成带图标的 **`Chzzk Rekoda.lnk`** 快捷方式。Linux 启动 GUI 时，会在用户应用菜单中注册图标和启动项。

</details>

---

<a id="installation"></a>

## 2. 安装

**[下载程序 ZIP](https://github.com/munsy0227/Chzzk-Rekoda/archive/refs/heads/main.zip)** · **[GitHub 仓库](https://github.com/munsy0227/Chzzk-Rekoda)**

请阅读并按照与你正在使用的操作系统（Windows、Mac、Linux）对应的说明操作。
安装过程中出现语言选择界面时，请先选择想使用的语言。

### Windows 用户

**第 1 步：下载程序**

1. 点击上方的 **下载程序 ZIP**，或在 GitHub 仓库中点击绿色 **[Code]** 按钮。
2. 如果使用 Code 菜单，请点击 **[Download ZIP]**。如果已使用上方的直接下载链接，请跳过此步。
3. 解压下载的文件。（建议解压到“桌面”等容易找到的位置。）

（如果你可以使用 Git，请使用 Git。）

**第 2 步：运行安装程序**

1. 进入解压后的文件夹。
2. 找到 `install.bat` 文件并双击运行。
3. 黑色窗口会打开，并自动安装所需文件。可能需要一些时间，请等待。
4. 安装最后选择 **GUI / CLI**。GUI 完成安装后打开应用，CLI 启动终端设置菜单。

---

### macOS / Linux 用户

**第 1 步：打开终端**

- **Mac：** 按 `Command` + `Space`，搜索“终端”并运行。
- **Linux：** 运行你使用的终端应用。

**第 2 步：输入命令**
将下面的命令逐行复制到终端中，然后按 Enter。

1. **下载程序**
   ```bash
   git clone https://github.com/munsy0227/Chzzk-Rekoda.git
   cd Chzzk-Rekoda
   ```

2. **安装 FFmpeg（录制必需）**
   - **Mac 用户（需要 Homebrew）：**
     ```bash
     brew install ffmpeg
     ```
   - **Ubuntu/Debian 用户：**
     ```bash
     sudo apt install ffmpeg -y
     ```
   - **Arch Linux 用户：**
     ```bash
     sudo pacman -S ffmpeg uv
     ```

3. **运行安装脚本**
   ```bash
   ./install
   ```

选择 **1. GUI** 进入首次设置向导；选择 **2. CLI** 打开终端设置菜单。

---

<a id="cli"></a>

## 3. 使用 CLI

如果更喜欢终端，请在安装时选择 **2. CLI**。GUI 与 CLI 共用 `config.json`，无需重新添加频道。

### 添加频道与设置

必须先注册想要录制的主播，录制才会工作。  
如果安装后设置界面关闭了，请运行 `settings.bat`（Windows）或 `./settings`（Mac/Linux）。

1. 出现菜单后，按键盘数字进行选择。
   - **输入 `1` 后按 Enter**：Channel Settings（频道设置）
   - **输入 `1` 后按 Enter**：Add Channel（添加频道）

2. 选择 **添加频道的方式**。
   - **按频道名称搜索**：输入搜索词，然后从同时显示名称和 ID 的结果中选择要添加的频道。
   - **通过频道 ID 直接添加**：输入 CHZZK 频道 URL 末尾的 ID，程序会自动查询官方频道名称。

3. 确认查询到的 **频道名称和 ID**。
   - 已注册的 ID 会在搜索结果中标记，不能重复添加。
   - 如果已注册的其他 ID 使用相同名称，程序会显示现有 ID，便于区分同名频道。

4. 输入 **保存路径**。
   - 如果什么都不输入直接按 Enter，项目内会创建以官方频道名称命名的文件夹，并将录像保存到其中。
   - 如有需要，也可以输入其他文件夹名称或路径。

5. 如果显示的频道名称、ID 和保存路径正确，请输入 `Y`。

> **提示：** 要录制需要成人认证或会员认证的直播，请在设置菜单的 **4. NAVER 登录** 中选择通过新的 Chrome、Microsoft Edge 或 Firefox 窗口直接登录 NAVER 并导入 Cookie（NID_AUT、NID_SES），或手动输入 Cookie 值。首次使用浏览器登录方式时，准备兼容的驱动程序可能需要网络连接。
> **2. 录制与画质**设置格式、分割、分辨率与 FPS；**3. 编码**选择 H.264/HEVC/AV1；**5. 网络**设置 DoH；**6. 语言与日志**设置语言与文件日志。频道独立设置位于 **1. 频道管理 → 4. 频道分割与画质**。`0` 表示返回或退出。

### 开始录制

现在只要让程序保持运行即可。

#### Windows

双击文件夹中的 `chzzk_record.bat` 文件。

#### Mac / Linux

在终端中输入以下命令。
```bash
./chzzk_record
```

如果黑色窗口打开并显示文字，说明正在正常工作。  
**关闭此窗口会停止录制，请保持打开！**（可以最小化。）

---

<a id="faq"></a>

## 常见问题（FAQ）

**Q. 录制的文件在哪里？**
A. 如果没有另外指定保存路径，录像会保存在项目内以官方频道名称命名的文件夹中。 在 GUI 中选择频道并点击 **打开保存文件夹**，即可打开录像位置。

**Q. 如何关闭程序？**
A. GUI 中选择 **录制设置 → 完全退出程序**，等待录制文件处理完成后退出。默认关闭窗口会隐藏到托盘。CLI 中请在运行中的终端按 `Ctrl` + `C`。

**Q. 出现错误！**
A. 请到 [Issues](https://github.com/munsy0227/Chzzk-Rekoda/issues) 描述症状，我们可以帮助你。

---

## 免责声明及注意事项

- 本程序是根据 **MIT 许可证** 发布的开源软件。
- 软件按 **“原样（AS IS）”** 提供，因使用程序而产生的一切结果的法律责任完全由 **用户本人** 承担。
- **录制的视频不得在私人用途及主播指定范围之外未经许可使用，视频使用的一切责任由录制该视频的用户承担。**
- **上传完整视频的行为（无论公开或非公开）均违反版权法**，版权持有人可能提起诉讼。
- 为防止 Deepfake，**作为 AI 训练资料使用的行为也可能被禁止。**

### 版权相关示例（라디유）
- 版权已根据 라디유 的意愿委托给 Sandbox Network。
- 作为 AI 训练资料使用的行为同样属于版权侵权。
- 除官方粉丝社区外，剪辑不能上传到其他地方。（不限于公开或非公开）
- 即使遵守了指南，也可能根据 라디유 或 Sandbox Network 的判断被删除。

### 非官方项目说明
本项目及贡献者与 **NAVER**、**CHZZK** 或其关联公司及子公司不存在任何合作、授权、批准或官方连接关系。本项目是为了提供便利而开发的独立、非营利、非官方程序。

### 商标说明
包括 “CHZZK”、“NAVER” 在内的相关名称、标志、徽章和图像均为相应所有者的注册商标。这些商标仅用于识别和引用目的，不暗示与商标权人的任何关联。本项目明确声明无意侵犯相关商标权或对商标权人造成损害。

### 版权和条款遵守
本项目不主张对流媒体视频、音频或其他第三方内容拥有所有权，也不授予这些内容的任何许可。用户有责任自行确认并遵守相关版权法、平台政策（如 CHZZK 使用条款等）和当地法律。通过本项目进行保存、复制、分发、传输或商业使用的责任完全由用户承担。
