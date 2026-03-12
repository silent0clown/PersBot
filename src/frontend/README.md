# PersBot 前端文档

## 概述

PersBot前端是一个基于Electron和React的桌面应用程序，提供3D卡通宠物形象、系统托盘集成、WebSocket通信等功能。前端与Python后端通过WebSocket进行实时通信，实现语音唤醒、AI对话和应用控制。

## 技术栈

### 核心框架
- **Electron**: 跨平台桌面应用框架
- **React**: 前端UI框架 (v18+)
- **TypeScript**: 静态类型检查
- **Vite**: 快速构建工具

### 3D图形
- **Three.js**: WebGL 3D渲染引擎
- **@react-three/fiber**: React Three.js绑定
- **@react-three/drei**: Three.js实用组件库
- **FBXLoader**: FBX模型加载器

### 状态管理
- **React Hooks**: useState, useEffect, useRef等
- **Context API**: 全局状态管理（WebSocket连接）

### 构建工具
- **ESLint**: 代码规范检查
- **Prettier**: 代码格式化
- **TypeScript Compiler**: 类型检查

## 项目结构

```
src/frontend/
├── electron/              # Electron主进程代码
│   ├── main.ts           # 主进程入口
│   └── preload.ts        # 预加载脚本
├── src/                  # React前端代码
│   ├── components/       # React组件
│   │   ├── BotAvatar.tsx # 3D宠物组件（支持FBX模型）
│   │   ├── TrayIcon.tsx  # 系统托盘组件
│   │   └── WebSocketManager.tsx # WebSocket管理
│   ├── App.tsx           # 主应用组件
│   ├── main.tsx          # React入口
│   └── types/            # TypeScript类型定义
├── res/                  # 资源文件
│   └── models/           # 3D模型文件
│       └── dog/          # 狗狗模型
│           └── dog_model.fbx # FBX格式宠物模型
├── public/               # 静态资源
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript配置
└── vite.config.ts        # Vite构建配置
```

## 功能特性

### 3D宠物形象
- **自定义FBX模型**: 支持加载任意FBX格式的3D模型
- **状态动画**: 根据不同状态（待机、听音、思考、说话）显示不同动画
- **实时交互**: 通过WebSocket接收后端状态更新

### 系统集成
- **系统托盘**: Windows系统托盘图标和菜单
- **窗口管理**: 最小化到托盘、双击显示/隐藏
- **跨平台**: 支持Windows、macOS、Linux

### 通信协议
- **WebSocket**: 与后端实时双向通信
- **消息类型**: 
  - `wake_word`: 唤醒词检测
  - `thinking`: AI处理中
  - `response`: AI回复文本
  - `audio`: 语音数据
  - `idle`: 空闲状态
  - `error`: 错误信息

## 开发环境

### 前置要求
- **Node.js**: v18+
- **npm/yarn**: 包管理器
- **Python**: 3.8+ (用于后端)
- **操作系统**: Windows 10/11, macOS, Linux

### 安装依赖
```bash
cd src/frontend
npm install
```

### 开发模式
```bash
# 启动Electron开发模式（自动重启）
npm run electron:dev

# 单独启动React开发服务器
npm run dev
```

### 构建发布
```bash
# 构建生产版本
npm run build

# 构建Electron可执行文件
npm run electron:build
```

## 自定义宠物模型

### 模型要求
- **格式**: FBX (.fbx)
- **路径**: `public/res/models/{petType}/{petType}_model.fbx`
- **材质**: 支持标准PBR材质
- **骨骼**: 可选（如果需要动画）

### 当前模型
- **类型**: 狗狗 (dog)
- **路径**: `public/res/models/dog/dog_model.fbx`
- **状态**: 已配置为默认宠物模型

### 添加新模型
1. 将FBX模型文件放入 `public/res/models/{petType}/` 目录
2. 更新`BotAvatar.tsx`中的模型路径配置
3. 如需动画，确保模型包含相应的动画剪辑

## WebSocket通信

### 连接地址
- **默认**: `ws://localhost:8000/ws`
- **可配置**: 通过环境变量修改

### 消息格式
```typescript
// 发送到后端
{
  type: "audio",      // 音频数据
  data: base64String
}

{
  type: "stop_wake"   // 停止唤醒词检测
}

// 从后端接收
{
  type: "wake_word"   // 检测到唤醒词
}

{
  type: "thinking"    // AI正在思考
}

{
  type: "response",   // AI回复
  content: "Hello!"
}

{
  type: "audio",      // 语音回复
  data: base64String
}

{
  type: "idle"        // 空闲状态
}

{
  type: "error",      // 错误信息
  message: "Error message"
}
```

## 故障排除

### 常见问题

1. **模型无法加载**
   - 检查FBX文件路径是否正确
   - 确保模型格式兼容（建议使用Blender导出）
   - 查看浏览器开发者工具中的网络和控制台错误

2. **WebSocket连接失败**
   - 确保后端服务正在运行 (`python src/backend/main.py`)
   - 检查端口配置（默认8000）
   - 防火墙可能阻止连接

3. **Electron启动缓慢**
   - 首次启动需要编译原生模块
   - 确保Node.js版本兼容

### 调试技巧
- 打开开发者工具：`Ctrl+Shift+I` (Windows/Linux) 或 `Cmd+Option+I` (macOS)
- 查看控制台日志了解错误详情
- 使用React DevTools调试组件状态

## 扩展开发

### 添加新功能
1. 在`components/`目录创建新组件
2. 在`App.tsx`中集成组件
3. 如需与后端通信，使用`WebSocketManager`

### 修改宠物行为
- 编辑`BotAvatar.tsx`中的动画逻辑
- 调整材质和光照效果
- 添加新的状态类型到`BotState`类型定义

### 国际化支持
- 当前支持中文界面
- 可通过添加语言包扩展多语言支持

## 性能优化

### 3D渲染优化
- 使用`drei`的性能优化组件
- 合理设置材质属性减少计算
- 避免过度复杂的模型

### 内存管理
- 及时清理WebSocket连接
- 优化Electron进程间通信
- 监控内存使用情况

## 许可证

MIT License - 详见项目根目录LICENSE文件