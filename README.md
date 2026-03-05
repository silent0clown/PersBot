# PersBot - 桌面贾维斯助手

一个具有卡通形象的智能桌面助手，具备语音唤醒、语音对话、电脑控制等功能。

## 功能特性

- 🤖 **3D卡通形象** - 可爱的机器人形象，表情会随状态变化
- 🎤 **语音唤醒** - 支持离线唤醒词检测
- 💬 **智能对话** - 本地大语言模型，理解你的指令
- 🔊 **语音合成** - 自然流畅的语音回复
- 📱 **APP控制** - 语音控制打开/关闭应用程序
- 💻 **桌面集成** - 系统托盘、悬浮窗口

## 技术栈

- **前端**: Electron + React + Three.js
- **后端**: Python + FastAPI
- **语音**: faster-whisper, Porcupine, Edge-TTS
- **AI**: Ollama + Qwen/ChatGLM
- **控制**: pywinauto, pyautogui

## 快速开始

### 前置要求

- Windows 10/11
- Python 3.10+
- Node.js 18+
- Ollama (本地运行大模型)

### 1. 克隆项目

```bash
git clone <repo-url>
cd PersBot
```

### 2. 安装后端依赖

```bash
cd src/backend
conda create -n persbot python=3.11
conda activate persbot
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd src/frontend
npm install
```

### 4. 启动 Ollama

确保本地运行 Ollama 并下载模型:

```bash
ollama pull qwen:7b
ollama serve
```

### 5. 启动开发模式

终端1 - 启动后端:
```bash
cd src/backend
python main.py
```

终端2 - 启动前端:
```bash
cd src/frontend
npm run electron:dev
```

## 项目结构

```
PersBot/
├── SPEC.md                 # 技术规格文档
├── src/
│   ├── frontend/           # Electron前端
│   │   ├── electron/       # Electron主进程
│   │   ├── src/
│   │   │   ├── components/ # React组件
│   │   │   └── App.tsx
│   │   └── package.json
│   └── backend/            # Python后端
│       ├── core/
│       │   ├── wake_word/  # 语音唤醒
│       │   ├── asr/       # 语音识别
│       │   ├── llm/       # 对话大脑
│       │   ├── tts/       # 语音合成
│       │   └── controller/# APP控制
│       └── main.py
```

## 使用说明

### 语音命令示例

- "打开微信" - 打开微信
- "打开浏览器" - 打开Chrome
- "截图" - 截取屏幕
- "最小化" - 最小化窗口
- 直接对话 - 智能问答

### 快捷操作

- 托盘图标双击 - 显示/隐藏窗口
- 托盘右键 - 打开菜单

## 配置

可以在 `src/backend/core/` 目录下各模块中修改配置:

- 唤醒词: `wake_word/wake_word_detector.py`
- 语音识别: `asr/asr_engine.py`  
- 对话模型: `llm/llm_client.py`
- 语音合成: `tts/tts_engine.py`
- APP映射: `controller/app_controller.py`

### 环境变量

- `PORCUPINE_ACCESS_KEY`: Porcupine唤醒词检测的访问密钥（可选）
- `OLLAMA_HOST`: Ollama服务器地址，默认为 `http://localhost:11434`

### 依赖说明

- **后端**: Python 3.10+, FastAPI, faster-whisper, pvporcupine, ollama
- **前端**: Node.js 18+, Electron, React, Three.js
- **系统**: Windows 10/11 (推荐), Linux/MacOS (部分功能可能受限)

## 构建发布

```bash
cd src/frontend
npm run electron:build
```

## 常见问题

### Q: GTX 960 能跑大模型吗?
A: 推荐使用 7B 参数模型，如 Qwen:7b 或 ChatGLM3-6B

### Q: 需要联网吗?
A: 语音唤醒和识别可离线运行，对话需要 Ollama

### Q: 如何自定义唤醒词?
A: 使用 Porcupine 训练自定义唤醒词模型

## License

MIT
