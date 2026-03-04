# PersBot - 桌面贾维斯助手

> 基于 Electron + Python 构建的智能桌面助手

## 1. 项目概述

**PersBot** 是一个具有卡通形象的智能桌面助手，具备语音唤醒、语音对话、电脑控制等功能。

### 目标用户
- 需要桌面助手提升工作效率的用户
- 追求个性化AI体验的用户

### 硬件环境
- CPU: Intel i7 9700
- GPU: GTX 960 4GB
- RAM: 32GB
- OS: Windows 10/11

---

## 2. 技术架构

```
┌─────────────────────────────────────────────┐
│              Electron 前端                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │
│  │ 3D/2D   │  │ 语音    │  │ 系统托盘    │ │
│  │ 卡通形象│  │ 可视化  │  │ 窗口管理    │ │
│  └─────────┘  └─────────┘  └─────────────┘ │
└──────────────────┬──────────────────────────┘
                   │ IPC / WebSocket
                   ▼
┌─────────────────────────────────────────────┐
│              Python 后端                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ 语音识别  │ │ 对话大脑  │ │ APP控制    │ │
│  │ Whisper  │ │ Ollama   │ │ pywinauto  │ │
│  └──────────┘ └──────────┘ └────────────┘ │
└─────────────────────────────────────────────┘
```

### 技术选型

| 模块 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 前端框架 | Electron | ^28.0.0 | 桌面应用框架 |
| UI库 | React | ^18.2.0 | UI组件化 |
| 3D形象 | Three.js / React Three Fiber | ^0.160.0 | 3D渲染 |
| 语音唤醒 | Porcupine | ^5.0.0 | 离线唤醒词 |
| 语音识别 | faster-whisper | ^0.10.0 | 本地ASR |
| 对话模型 | Ollama + Qwen | latest | 本地LLM |
| 语音合成 | Edge-TTS | - | 在线TTS |
| APP控制 | pywinauto | ^0.6.8 | Windows自动化 |
| 进程通信 | python-node-connector | - | IPC桥接 |

---

## 3. 功能规格

### 3.1 桌面形象

- **形象设计**: 2D卡通机器人 / 3D虚拟形象
- **表情系统**: 
  - 待机状态 (眨眼、呼吸)
  - 聆听状态 (眼睛转动)
  - 说话状态 (嘴巴动画)
  - 执行状态 (思考/忙碌)
  - 错误状态 (哭泣/无奈)
- **交互方式**: 拖拽移动、点击交互
- **显示位置**: 桌面悬浮窗 / 系统托盘

### 3.2 语音唤醒

- **唤醒词**: "小Jarvis" / "贾维斯" / 自定义
- **唤醒方式**: 
  - 关键词唤醒 (Porcupine)
  - 持续监听模式
- **反馈**: 唤醒成功音效 + 视觉反馈

### 3.3 语音对话

- **流程**: 唤醒 → 监听 → 识别 → 对话 → 合成 → 播放
- **语音识别**: faster-whisper (支持中英文)
- **对话理解**: 本地 Ollama (Qwen/ChatGLM)
- **语音合成**: Edge-TTS (自然人声)

### 3.4 APP控制

- **打开应用**: "打开微信"、"打开浏览器"
- **关闭窗口**: "关闭窗口"
- **截图**: "截图"
- **更多**: 支持自定义命令扩展

---

## 4. 目录结构

```
PersBot/
├── docs/                    # 项目文档
├── src/
│   ├── frontend/           # Electron前端
│   │   ├── src/
│   │   │   ├── components/ # React组件
│   │   │   ├── hooks/      # 自定义Hooks
│   │   │   ├── assets/    # 静态资源
│   │   │   └── App.tsx
│   │   ├── electron/       # Electron主进程
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── backend/            # Python后端
│       ├── core/           # 核心模块
│       │   ├── wake_word/  # 语音唤醒
│       │   ├── asr/       # 语音识别
│       │   ├── llm/       # 对话大脑
│       │   ├── tts/       # 语音合成
│       │   └── controller/# APP控制
│       ├── requirements.txt
│       └── main.py
├── SPEC.md                 # 技术规格文档
└── README.md               # 项目说明
```

---

## 5. 依赖环境

### Python 环境
```bash
# Python 3.10+
conda create -n persbot python=3.11
conda activate persbot

# 核心依赖
pip install faster-whisper
pip install pvporcupine
pip install pywinauto
pip install pyttsx3
pip install websocket-server
pip install numpy
```

### Node.js 环境
```bash
# Node.js 18+
cd src/frontend
npm install
```

### 本地模型
```bash
# Ollama (本地运行大模型)
# 下载: https://github.com/ollama/ollama

# Whisper模型
# 首次运行自动下载 (tiny/base/small)
```

---

## 6. 配置文件

### 唤醒词配置
```json
{
  "wake_word": {
    "keywords": ["jarvis", "贾维斯"],
    "sensitivity": 0.5
  }
}
```

### 对话模型配置
```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen:7b",
    "temperature": 0.7
  }
}
```

### APP控制映射
```json
{
  "apps": {
    "微信": "WeChat",
    "浏览器": "chrome",
    "记事本": "notepad",
    "文件管理器": "explorer"
  }
}
```

---

## 7. 开发指南

### 启动开发模式

1. 启动后端:
```bash
cd src/backend
python main.py
```

2. 启动前端:
```bash
cd src/frontend
npm run dev
```

### 构建发布
```bash
# 前端构建
cd src/frontend
npm run build

# 打包 Electron
npm run electron:build
```

---

## 8. 里程碑

- [ ] Phase 1: 项目骨架搭建
- [ ] Phase 2: Electron 窗口与托盘
- [ ] Phase 3: 卡通形象 UI
- [ ] Phase 4: 语音唤醒 + 识别
- [ ] Phase 5: 对话功能
- [ ] Phase 6: APP 控制
- [ ] Phase 7: 优化与打包

---

## 9. 常见问题

**Q: GTX 960 能跑大模型吗?**
A: 推荐用 7B 参数模型，Qwen:7b 或 ChatGLM3-6B 可以在 4-6GB 显存运行。

**Q: 需要联网吗?**
A: 语音唤醒和识别可离线，对话需要 Ollama 运行在本地。

**Q: 如何自定义唤醒词?**
A: 在 Porcupine 后台训练自定义唤醒词模型。
