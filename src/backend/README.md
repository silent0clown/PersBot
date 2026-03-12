# PersBot Backend Documentation

## 概述

PersBot后端是一个基于FastAPI的AI助手服务，提供语音识别、大语言模型集成、文本转语音和应用控制功能。后端支持多种大语言模型提供商，包括Ollama本地部署和OpenAI API。

## 系统架构

### 核心组件

- **Wake Word Detector**: 唤醒词检测（使用Porcupine）
- **ASR Engine**: 语音识别（使用Faster-Whisper）
- **LLM Client**: 大语言模型客户端（支持Ollama和OpenAI API）
- **TTS Engine**: 文本转语音（使用pyttsx3）
- **App Controller**: 应用控制（Windows自动化）

### 技术栈

- **Web框架**: FastAPI
- **异步处理**: asyncio
- **WebSocket**: 实时通信
- **环境配置**: python-dotenv

## 配置管理

后端通过`.env`文件进行配置管理。创建`.env`文件并根据需要配置以下参数：

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_PROVIDER` | LLM提供商 (`ollama`, `openai`, `other`) | `ollama` |
| `OLLAMA_BASE_URL` | Ollama服务器地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama模型名称 | `qwen:7b` |
| `OPENAI_API_KEY` | OpenAI API密钥 | (必需) |
| `OPENAI_BASE_URL` | OpenAI API地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | OpenAI模型名称 | `gpt-3.5-turbo` |
| `OTHER_API_KEY` | 其他API密钥 | (必需) |
| `OTHER_BASE_URL` | 其他API地址 | `http://localhost:11434` |
| `OTHER_MODEL` | 其他模型名称 | `qwen:7b` |

### 配置示例

**使用Ollama (本地部署):**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen:7b
```

**使用OpenAI API:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo
```

**使用其他OpenAI兼容API (如Together AI, DeepSeek等):**
```env
LLM_PROVIDER=other
OTHER_API_KEY=your-api-key
OTHER_BASE_URL=https://api.together.ai/v1
OTHER_MODEL=meta-llama/Llama-3-70b-chat-hf
```

## API 接口

### WebSocket 端点

- **`/ws`**: 实时双向通信
  - **音频数据**: `{"type": "audio", "data": <base64_encoded_audio>}`
  - **停止唤醒词检测**: `{"type": "stop_wake"}`
  - **响应类型**: 
    - `{"type": "wake_word"}` - 检测到唤醒词
    - `{"type": "thinking"}` - 正在处理请求
    - `{"type": "response", "content": "..."}` - AI响应
    - `{"type": "audio", "data": <base64_encoded_audio>}` - 语音响应
    - `{"type": "idle"}` - 空闲状态
    - `{"type": "error", "message": "..."}` - 错误信息

### HTTP REST API

#### POST `/api/chat`
- **请求体**: `{"message": "用户消息"}`
- **响应**: `{"response": "AI回复"}` 或 `{"error": "错误信息"}`

#### POST `/api/control`
- **路径参数**: `command` - 控制命令字符串
- **响应**: `{"success": true, "result": "..."} ` 或 `{"error": "错误信息"}`

#### GET `/api/health`
- **响应**: 系统健康状态
```json
{
  "status": "ok",
  "components": {
    "wake_word": true,
    "asr": true,
    "llm": true,
    "tts": true,
    "controller": true
  }
}
```

## 安装与运行

### 依赖安装
```bash
cd src/backend
pip install -r requirements.txt
```

### 启动服务
```bash
cd src/backend
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 环境要求

- **Python**: 3.8+
- **Ollama**: 如果使用本地模型，需要安装Ollama并运行相应模型
- **Windows**: App Controller功能仅在Windows上可用

## 扩展性

### 添加新的LLM提供商
1. 在`.env`文件中添加相应的配置变量
2. 修改`LLMClient._init_client()`方法以支持新的提供商
3. 确保相应的Python包已添加到`requirements.txt`

### 自定义模型
通过修改`.env`文件中的模型参数，可以轻松切换不同的模型，无需修改代码。

## 故障排除

### 常见问题

1. **LLM客户端初始化失败**
   - 检查`.env`文件中的配置是否正确
   - 确保API密钥有效（如果使用API）
   - 确保Ollama服务正在运行（如果使用Ollama）

2. **缺少依赖包**
   - 运行 `pip install -r requirements.txt` 安装所有依赖

3. **WebSocket连接问题**
   - 检查CORS设置
   - 确保前端和后端在同一网络环境中

### 日志
后端使用标准Python logging，日志级别为INFO，可以在启动时查看组件初始化状态。