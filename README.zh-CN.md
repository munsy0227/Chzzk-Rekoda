# CHZZK Rekoda（Chzzk-Rekoda）

**语言：** [한국어](README.md) | [English](README.en.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

这是一个使用 Streamlink 和 FFmpeg 制作的 CHZZK 自动录制程序，支持 Windows、macOS 和 Linux。

它也是一个即使不熟悉电脑的人也能轻松使用的 **CHZZK 自动录制程序**。  
直播开始时会自动开始录制，直播结束后会自动保存。

[[教程] 在 Android 手机上安装程序](https://github.com/munsy0227/Chzzk-Rekoda/discussions/17)

[[TUTORIAL] How to Install Chzzk-Rekoda in Android Systems](https://github.com/munsy0227/Chzzk-Rekoda/discussions/18)

---

## 1. 安装（下载）

请阅读并按照与你正在使用的操作系统（Windows、Mac、Linux）对应的说明操作。
安装过程中出现语言选择界面时，请先选择想使用的语言。

### Windows 用户

**第 1 步：下载程序**
1. 点击此页面上方的绿色 **[Code]** 按钮。
2. 在菜单中点击 **[Download ZIP]** 下载压缩文件。
3. 解压下载的文件。（建议解压到“桌面”等容易找到的位置。）

（如果你可以使用 Git，请使用 Git。）

**第 2 步：运行安装程序**
1. 进入解压后的文件夹。
2. 找到 `install.bat` 文件并双击运行。
3. 黑色窗口会打开，并自动安装所需文件。可能需要一些时间，请等待。
4. 安装完成后，会自动显示设置界面。

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

---

## 2. 设置（添加频道）

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

> **提示：** 要录制需要成人认证或会员认证的直播，请在设置菜单的 **5. NAVER Cookie 设置** 中选择通过新的 Chrome、Microsoft Edge 或 Firefox 窗口直接登录 NAVER 并导入 Cookie（NID_AUT、NID_SES），或手动输入 Cookie 值。首次使用浏览器登录方式时，准备兼容的驱动程序可能需要网络连接。
> 保存扩展名可在 **2. Recording Settings** 中从 `ts`、`mkv`、`webm` 中选择，同一菜单还可以设置是否每隔几小时或几分钟分割录制文件。AV1 编码可在 **4. AV1 Settings** 中启用。遇到 DNS 问题时，可在 **6. DNS-over-HTTPS Settings** 中设置并启用 DoH 地址。语言可在 **8. Language Settings** 中从韩语、英语、简体中文、繁体中文、日语中选择。

---

## 3. 开始录制

现在只要让程序保持运行即可。

### Windows
双击文件夹中的 `chzzk_record.bat` 文件。

### Mac / Linux
在终端中输入以下命令。
```bash
./chzzk_record
```

如果黑色窗口打开并显示文字，说明正在正常工作。  
**关闭此窗口会停止录制，请保持打开！**（可以最小化。）

---

## 常见问题（FAQ）

**Q. 录制的文件在哪里？**
A. 如果没有另外指定保存路径，录像会保存在项目内以官方频道名称命名的文件夹中。

**Q. 如何关闭程序？**
A. 关闭正在运行的黑色窗口（终端），或点击该窗口后按键盘上的 `Ctrl` + `C`。

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
