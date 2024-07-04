#  Chzzk-Rekoda
Streamlink와 ffmpeg를 활용하여 만들어진 Windows, macOS, Linux를 지원하는 치지직 자동 녹화 프로그램입니다.

[[튜토리얼] 안드로이드 휴대폰에 프로그램 설치하기](https://github.com/munsy0227/Chzzk-Rekoda/discussions/17)

[[TUTORIAL] How to Install Chzzk-Rekoda in Android Systems](https://github.com/munsy0227/Chzzk-Rekoda/discussions/18)

## 설치 방법

### Windows
설치를 진행하기 전에 Python 3.10~3.12가 설치되어있는지 확인해 주시기를 바랍니다.

#### 1. 다운로드하기
1. Git이 설치된 경우 이 방법을 사용하세요.
```bash
git clone https://github.com/munsy0227/Chzzk-Rekoda.git
```
2. Git이 없는 경우 아래 링크에서 다운로드하세요. [아니면 이걸 클릭하세요](https://github.com/munsy0227/Chzzk-Rekoda/archive/refs/heads/main.zip)
```bash
https://github.com/munsy0227/Chzzk-Rekoda/archive/refs/heads/main.zip
```
#### 2. 설치하기
1. install.bat을 실행합니다.
```bash
install.bat
```
### macOS/Linux

#### 1. 클론하기
원하는 디렉터리로 가서 터미널을 실행하고 이 명령을 입력하세요.
```bash
git clone https://github.com/munsy0227/Chzzk-Rekoda.git
cd Chzzk-Rekoda
```
#### 2. ffmpeg 설치
ffmpeg가 이미 설치되어 있으면 건너뜁니다.
1. macOS 일 경우
```bash
brew install ffmpeg
```
2. ubuntu, 데비안 일 경우
```bash
sudo apt install ffmpeg
```
3. ArchLinux 일 경우
```bash
sudo pacman -S ffmpeg
```
#### 3. 설치하기
```bash
./install
```

## 사용 방법
chzzk_record.bat 혹은 chzzk_record를 실행하여 녹화한다.
### Windows
```bash
chzzk_record.bat
```
### macOS/Linux
```bash
./chzzk_record
```

settings.bat 혹은 settings를 실행하여 설정한다.
### Windows
```bash
settings.bat
```
### macOS/Linux
```bash
./settings
```
