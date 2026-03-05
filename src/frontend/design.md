# PersBot 前端技术设计文档

## 技术栈选型

### 核心组合
- **Three.js + React Three Fiber (R3F)**: 3D 渲染引擎，负责加载模型、渲染场景、光照、阴影
- **GSAP**: 平滑动画和缓动效果
- **Cannon.js** (可选): 物理引擎
- **Zustand**: 状态管理

### 模块详细说明

| 模块 | 推荐库/工具 | 作用 |
|------|------------|------|
| 3D 渲染引擎 | Three.js (底层) 或 React Three Fiber (R3F) (推荐) | 负责加载模型、渲染场景、光照、阴影。R3F 让 Three.js 在 React 中像写组件一样简单。 |
| 动画系统 | Three.js AnimationMixer | 解析 .glb/.gltf 文件中的骨骼动画，控制播放、暂停、混合（如从走路平滑过渡到站立）。 |
| 交互逻辑 | Raycaster (光线投射) | 核心！用于检测鼠标是否点击了 3D 物体，获取点击坐标。 |
| 平滑运动 | GSAP 或 TWEEN.js | 让宠物的移动、转头动作有缓动效果（Easing），避免生硬的瞬移。 |
| 状态管理 | Zustand / Redux / Vue Reactivity | 管理宠物的"饥饿值"、"心情值"，驱动动画切换。 |
| 桌面穿透 | Electron (Windows/Mac) | 如果要做成桌面挂件，需要 Electron 设置 transparent: true, frame: false, alwaysOnTop: true 以及鼠标事件穿透 (pointer-events: none 的动态切换)。 |

## 宠物能力

### 核心功能实现原理

#### A. 饿了、饱了的动作实现（状态机驱动）
这不是靠"猜"，而是靠状态机 (State Machine) 驱动动画混合。

**准备动画资源：**
需要在模型中包含（或通过 Mixamo 添加）以下动画片段（Clips）：
- Idle_Normal (普通待机)
- Idle_Hungry (饥饿待机，比如摸肚子、发抖)
- Eat (吃东西)
- Happy (吃饱了开心跳舞)

**状态机逻辑：**
- 当饥饿值 < 阈值时，切换到 Idle_Hungry 动画
- 当用户喂食时，播放 Eat 动画
- 吃完后播放 Happy 动画，然后回到 Idle_Normal
- 使用 AnimationMixer 进行动画混合，实现平滑过渡

#### B. 鼠标交互实现
- 使用 Raycaster 检测鼠标点击事件
- 当鼠标悬停在宠物上时，显示交互提示
- 点击宠物可以触发不同的反应（抚摸、喂食等）
- 拖拽功能允许用户移动宠物位置

#### C. 桌面挂件功能
- 使用 Electron 实现桌面穿透
- 支持 alwaysOnTop 保持在最上层
- 动态切换 pointer-events 实现鼠标穿透/交互切换
- 支持拖拽到桌面任意位置

## 文件结构规划
```
src/frontend/
├── components/
│   ├── PetContainer.tsx      # 宠物容器组件
│   ├── PetModel.tsx          # 3D 模型组件
│   └── Controls.tsx          # 控制面板组件
├── hooks/
│   ├── usePetState.ts        # 宠物状态管理 hook
│   └── useAnimation.ts       # 动画控制 hook
├── store/
│   └── petStore.ts           # Zustand 状态存储
├── utils/
│   ├── raycaster.ts          # 光线投射工具
│   └── animationUtils.ts     # 动画工具函数
└── design.md                 # 本设计文档
```