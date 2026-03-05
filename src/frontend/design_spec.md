# PersBot 3D桌面宠物设计方案

## 1. 技术栈架构

### 1.1 核心技术栈
- **主框架**: React 18 + TypeScript
- **3D渲染**: Three.js + React Three Fiber (R3F)
- **状态管理**: Zustand
- **动画系统**: Three.js AnimationMixer + GSAP
- **物理引擎**: Cannon.js (可选，用于高级交互)
- **桌面应用**: Electron 28+
- **构建工具**: Vite 4

### 1.2 辅助库
- **UI组件**: @mui/material (设置面板、上下文菜单)
- **工具库**: lodash, date-fns
- **类型检查**: TypeScript strict mode
- **代码质量**: ESLint + Prettier + Husky

### 1.3 架构模式
```
┌─────────────────┐
│   Electron App  │ ← 桌面容器层
└────────┬────────┘
         │
┌────────▼────────┐
│   React App     │ ← 应用逻辑层
└────────┬────────┘
         │
┌────────▼────────┐
│   R3F + Three.js│ ← 3D渲染层
└────────┬────────┘
         │
┌────────▼────────┐
│   Model Assets  │ ← 资源层
└─────────────────┘
```

## 2. 模块设计

### 2.1 核心模块划分

#### 状态管理模块 (`store/`)
- `petStore.ts`: 主状态存储，包含饥饿值、心情值、体力值、清洁度
- `settingsStore.ts`: 用户设置存储
- `positionStore.ts`: 位置和窗口状态存储

#### 3D渲染模块 (`components/3d/`)
- `PetScene.tsx`: 主场景组件
- `PetModel.tsx`: 宠物模型组件
- `Environment.tsx`: 环境光照组件
- `Effects.tsx`: 后处理效果（如毛发光泽）

#### 交互模块 (`components/interaction/`)
- `RaycasterManager.tsx`: 光线投射管理器
- `DragHandler.tsx`: 拖拽处理器
- `ContextMenu.tsx`: 右键菜单组件
- `Tooltip.tsx`: 状态提示气泡

#### 动画系统 (`hooks/animation/`)
- `useAnimationController.ts`: 动画控制器hook
- `useStateMachine.ts`: 状态机hook
- `useBlendAnimations.ts`: 动画混合hook

#### 智能行为模块 (`services/behavior/`)
- `BehaviorScheduler.ts`: 行为调度器
- `EnvironmentMonitor.ts`: 环境监控器
- `StateDrivenBehavior.ts`: 状态驱动行为

#### 桌面集成模块 (`services/desktop/`)
- `WindowManager.ts`: 窗口管理
- `MousePassthrough.ts`: 鼠标穿透控制
- `PositionManager.ts`: 位置管理

### 2.2 数据流设计
```
用户交互 → 交互模块 → 状态管理 → 动画系统 → 3D渲染
    ↑                                   ↓
    └── 智能行为 ← 状态管理 ←──────────┘
```

## 3. 资源规划

### 3.1 3D模型资源
- **格式**: GLB/GLTF (推荐GLB，单文件便于管理)
- **来源**: 
  - Mixamo (基础动画)
  - 自定义建模 (特殊模型和配件)
  - CC0资源库 (备用)
- **规格要求**:
  - 顶点数: < 10,000
  - 材质: PBR材质
  - 动画: 包含所有需求文档中的动画片段
  - LOD: 支持2级LOD（高配/低配）

### 3.2 动画资源清单
- **基础待机**: Idle_Normal, Idle_Hungry, Idle_Happy, Idle_Sleepy, Idle_Dirty
- **交互动作**: Pet_Caress, Eat_Normal, Eat_Favorite, Clean_Bath, Wake_Up
- **特殊动作**: Happy_Dance, Sick_Animation, Play_Seek, Sleep_Animation
- **过渡动画**: 所有状态间平滑过渡

### 3.3 音频资源
- **格式**: MP3/Ogg
- **音效类型**:
  - 交互反馈音效（抚摸、喂食、清洁）
  - 状态变化音效（饥饿、开心、疲惫）
  - 环境音效（背景音乐、节日音效）
- **音量控制**: 支持全局音量调节

### 3.4 图标和UI资源
- **格式**: SVG/PNG
- **内容**:
  - 状态图标（饥饿、心情、体力、清洁度）
  - 菜单图标（喂食、清洁、设置等）
  - 配件图标（帽子、眼镜等）

## 4. 关键技术实现方案

### 4.1 状态机设计
```typescript
interface PetState {
  hunger: number;    // 0-100
  mood: number;      // 0-100  
  energy: number;    // 0-100
  cleanliness: number; // 0-100
}

enum AnimationState {
  IDLE_NORMAL = 'idle_normal',
  IDLE_HUNGRY = 'idle_hungry',
  IDLE_HAPPY = 'idle_happy',
  EATING = 'eating',
  SLEEPING = 'sleeping',
  // ... 其他状态
}

class AnimationStateMachine {
  private currentState: AnimationState;
  private mixer: AnimationMixer;
  
  transition(targetState: AnimationState, blendDuration: number = 0.5): void {
    // 实现平滑过渡
  }
}
```

### 4.2 动画混合策略
- **权重计算**: 基于状态值动态计算动画权重
  ```javascript
  // 例如：饥饿动画权重 = (100 - hunger) / 100
  const hungryWeight = Math.max(0, (20 - hunger) / 20);
  const normalWeight = 1 - hungryWeight;
  ```
- **优先级系统**: 
  - 交互动画 > 状态动画 > 随机动画
  - 睡眠状态具有最高优先级

### 4.3 鼠标交互实现
- **Raycaster配置**:
  ```javascript
  const raycaster = new Raycaster();
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects([petModel]);
  ```
- **穿透控制**:
  ```javascript
  // Electron主进程
  mainWindow.setIgnoreMouseEvents(true); // 默认穿透
  // 渲染进程检测悬停
  if (isHovering) {
    ipcRenderer.send('disable-passthrough');
  }
  ```

### 4.4 性能优化策略
- **渲染优化**:
  - 使用Drei的`useGLTF`进行模型预加载
  - 启用Three.js的frustum culling
  - 使用instanced rendering（如果有多宠物）
- **内存管理**:
  - 动画clip缓存池
  - 资源按需加载/卸载
- **降级策略**:
  - 低配设备禁用后处理效果
  - 简化动画（减少同时播放的动画数量）
  - 降低渲染分辨率

## 5. 文件结构规划

```
src/
├── main/                    # Electron主进程
│   ├── index.ts
│   └── windowManager.ts
├── renderer/                # React渲染进程
│   ├── App.tsx
│   ├── components/
│   │   ├── layout/          # 布局组件
│   │   ├── 3d/              # 3D相关组件
│   │   ├── interaction/     # 交互组件
│   │   └── ui/              # UI组件
│   ├── hooks/
│   │   ├── animation/       # 动画相关hooks
│   │   └── utils/           # 工具hooks
│   ├── store/               # Zustand状态存储
│   ├── services/            # 业务逻辑服务
│   │   ├── behavior/        # 智能行为
│   │   └── desktop/         # 桌面集成
│   ├── assets/              # 静态资源
│   │   ├── models/          # 3D模型
│   │   ├── sounds/          # 音频文件
│   │   └── icons/           # 图标
│   └── utils/               # 工具函数
└── types/                   # TypeScript类型定义
```

## 6. 开发路线图

### 6.1 第一阶段：基础框架搭建
- [ ] Electron应用基础结构
- [ ] React + R3F集成
- [ ] 基础3D场景和模型加载
- [ ] 简单鼠标交互

### 6.2 第二阶段：核心功能实现
- [ ] 状态管理系统
- [ ] 动画控制器和状态机
- [ ] 基础交互功能（抚摸、喂食）
- [ ] 桌面穿透和置顶

### 6.3 第三阶段：智能行为和优化
- [ ] 随机行为系统
- [ ] 环境感知功能
- [ ] 性能优化和降级策略
- [ ] 多模型支持

### 6.4 第四阶段：个性化和发布
- [ ] 设置面板和个性化选项
- [ ] 音效系统
- [ ] 打包和发布脚本
- [ ] 文档和用户指南

## 7. 测试策略

### 7.1 单元测试
- 状态管理逻辑
- 动画状态机
- 工具函数

### 7.2 集成测试
- 交互流程测试
- 状态联动测试
- 桌面集成功能

### 7.3 性能测试
- CPU/内存占用监控
- FPS稳定性测试
- 不同硬件配置兼容性测试

## 8. 风险评估和应对

### 8.1 技术风险
- **Three.js版本兼容性**: 锁定版本，定期更新测试
- **Electron性能问题**: 优化渲染，必要时考虑Tauri替代方案
- **模型加载性能**: 实现渐进式加载和缓存

### 8.2 资源风险
- **3D模型质量**: 预先制作原型验证
- **动画流畅度**: 使用专业动画工具，确保关键帧质量
- **跨平台兼容性**: 在多平台持续集成测试