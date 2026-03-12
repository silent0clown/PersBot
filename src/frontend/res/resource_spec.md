# PersBot 3D桌面宠物资源规格文档

## 1. 资源存储路径规划

### 1.1 整体目录结构
```
src/frontend/assets/
├── models/                  # 3D模型文件
│   ├── pets/               # 宠物主体模型
│   │   ├── default/        # 默认宠物模型
│   │   ├── cat/            # 猫咪模型
│   │   └── dog/            # 狗狗模型
│   └── accessories/         # 配件模型
│       ├── hats/           # 帽子
│       └── glasses/        # 眼镜
├── animations/             # 动画资源（如果单独存储）
├── sounds/                 # 音频文件
│   ├── effects/            # 音效
│   └── music/              # 背景音乐
├── textures/               # 纹理贴图
│   ├── pets/               # 宠物纹理
│   └── environment/        # 环境纹理
└── icons/                  # UI图标
```

### 1.2 具体文件路径规范
- **模型文件**: `src/frontend/assets/models/pets/{petType}/{petType}.glb`
- **动画文件**: `src/frontend/assets/animations/{petType}/{animationName}.glb`
- **音频文件**: `src/frontend/assets/sounds/effects/{effectName}.mp3`
- **纹理文件**: `src/frontend/assets/textures/pets/{petType}/{textureName}.png`

## 2. 3D模型规格

### 2.1 基础模型要求
- **格式**: GLB (Binary GLTF)
- **单位**: 米制
- **坐标系**: Y轴向上
- **顶点数**: 
  - 高配版: 8,000-10,000 vertices
  - 低配版: 3,000-5,000 vertices
- **材质**: PBR材质 (Metallic-Roughness workflow)
- **骨骼**: 
  - 主骨骼: 20-30 bones
  - 面部骨骼: 10-15 bones (用于表情变化)
- **LOD**: 支持2级细节层次

### 2.2 宠物角色形象描述

#### 默认宠物 (Default Pet)
- **外观**: 卡通风格的圆润小生物，类似仓鼠和兔子的混合体
- **尺寸**: 身高约0.15米，身长约0.2米
- **颜色**: 主色调为浅蓝色 (#87CEEB)，腹部为白色
- **特征**: 
  - 大眼睛，黑色瞳孔带白色高光
  - 圆润的身体和四肢
  - 短小的尾巴
  - 柔软的毛发质感
- **表情系统**: 支持基本表情变化（开心、难过、饥饿、困倦）

#### 猫咪模型 (Cat)
- **外观**: 写实卡通风格的短毛猫
- **尺寸**: 身高约0.12米，身长约0.25米
- **颜色**: 橘色虎斑纹 (#FFA500 + #8B4513)
- **特征**:
  - 尖耳朵，可独立转动
  - 长尾巴，可摆动
  - 灵活的四肢和身体
  - 猫咪特有的面部表情

#### 狗狗模型 (Dog)
- **外观**: 卡通柯基犬
- **尺寸**: 身高约0.1米，身长约0.22米
- **颜色**: 三色柯基 (#F5DEB3 + #8B4513 + #000000)
- **特征**:
  - 大耳朵，可轻微摆动
  - 短腿长身体
  - 蓬松的尾巴
  - 友好的面部表情

## 3. 动画资源详细规格

### 3.1 动画通用规格
- **格式**: GLB内嵌动画 (Animation Clips)
- **帧率**: 30 FPS
- **循环模式**: 根据动画类型设置 (Loop/Once/Clamp)
- **关键帧**: 平滑插值，避免突兀动作
- **命名规范**: `{state}_{action}_{variant}`

### 3.2 详细动画清单

#### Idle_Normal (普通待机)
- **文件路径**: `src/frontend/assets/animations/default/idle_normal.glb`
- **时长**: 8秒循环
- **动画内容**:
  - 缓慢呼吸（胸部轻微起伏）
  - 偶尔眨眼（每3-5秒一次）
  - 轻微头部转动（左右各15度，周期4秒）
  - 尾巴缓慢摆动（如果适用）
- **角色姿态**: 自然站立或坐姿，身体放松
- **权重**: 基础权重1.0，其他状态为0时播放

#### Idle_Hungry (饥饿待机)
- **文件路径**: `src/frontend/assets/animations/default/idle_hungry.glb`
- **时长**: 6秒循环
- **动画内容**:
  - 频繁摸肚子（每2秒一次，右手抬起轻拍腹部）
  - 身体轻微发抖（全身高频小幅度震动）
  - 焦虑表情（眉毛下垂，嘴角向下）
  - 频繁看向用户方向（头部快速转向屏幕外）
  - 发出轻微咕噜声（配合音效）
- **角色姿态**: 蜷缩身体，显得虚弱
- **触发条件**: 饥饿值 < 20

#### Idle_Happy (开心待机)
- **文件路径**: `src/frontend/assets/animations/default/idle_happy.glb`
- **时长**: 5秒循环
- **动画内容**:
  - 摇尾巴（快速摆动，幅度大）
  - 跳跃动作（每3秒轻微跳起）
  - 开心表情（大眼睛，微笑，脸颊微红）
  - 转圈（偶尔原地小转圈）
  - 发出开心的呼噜声
- **角色姿态**: 活跃站立，身体前倾表示兴奋
- **触发条件**: 心情值 > 80 且 饥饿值 > 60

#### Idle_Sleepy (困倦待机)
- **文件路径**: `src/frontend/assets/animations/default/idle_sleepy.glb`
- **时长**: 10秒循环
- **动画内容**:
  - 打哈欠（每8秒一次，张大嘴巴，伸懒腰）
  - 揉眼睛（双手揉眼，每5秒一次）
  - 眼皮下垂（眼部骨骼控制）
  - 身体摇晃（站立不稳，轻微左右摇摆）
  - 寻找舒适位置（缓慢移动到角落）
- **角色姿态**: 蜷缩或半躺，显得疲惫
- **触发条件**: 体力值 < 30 或 夜间时间(22:00-6:00)

#### Idle_Dirty (脏乱待机)
- **文件路径**: `src/frontend/assets/animations/default/idle_dirty.glb`
- **时长**: 7秒循环
- **动画内容**:
  - 抓痒（频繁抓挠身体各部位）
  - 甩头（试图甩掉灰尘）
  - 嫌弃表情（皱眉，撇嘴）
  - 身体抖动（试图抖掉脏东西）
  - 毛发暗淡特效（通过材质参数控制）
- **角色姿态**: 不舒服的姿势，经常变换位置
- **触发条件**: 清洁度 < 30

#### Eat_Normal (正常进食)
- **文件路径**: `src/frontend/assets/animations/default/eat_normal.glb`
- **时长**: 4秒 (一次性播放)
- **动画内容**:
  - 低头看向食物（头部向下45度）
  - 双手拿起食物（手臂自然弯曲）
  - 咀嚼动作（下颌开合，每秒2次）
  - 吞咽动作（喉部轻微移动）
  - 满足表情（眼睛微闭，嘴角上扬）
  - 吃完后抬头（恢复自然姿态）
- **角色姿态**: 坐姿，专注进食
- **触发条件**: 用户选择喂食普通食物

#### Eat_Favorite (喜欢的食物)
- **文件路径**: `src/frontend/assets/animations/default/eat_favorite.glb`
- **时长**: 5秒 (一次性播放)
- **动画内容**:
  - 兴奋跳跃（看到食物时先跳起）
  - 快速抓取食物（急切的动作）
  - 贪婪咀嚼（更快的咀嚼频率）
  - 心形眼睛特效（眼部材质变化）
  - 吃完后跳舞（2秒庆祝动作）
  - 特殊音效（满足的叫声）
- **角色姿态**: 极度兴奋，动作夸张
- **触发条件**: 用户选择喂食喜欢的食物

#### Pet_Caress (被抚摸)
- **文件_path**: `src/frontend/assets/animations/default/pet_caress.glb`
- **时长**: 3秒 (一次性播放)
- **动画内容**:
  - 身体跟随鼠标移动（平滑追踪）
  - 享受表情（眼睛半闭，微笑）
  - 发出呼噜声（持续音效）
  - 身体轻微起伏（配合抚摸节奏）
  - 尾巴愉快摆动
- **角色姿态**: 放松享受，微微倾斜身体
- **触发条件**: 用户左键点击并拖动

#### Clean_Bath (清洁洗澡)
- **文件_path**: `src/frontend/assets/animations/default/clean_bath.glb`
- **时长**: 6秒 (一次性播放)
- **动画内容**:
  - 初始抗拒（后退一步，惊讶表情）
  - 接受清洁（站定不动）
  - 享受洗澡（闭眼享受）
  - 甩水动作（快速全身抖动）
  - 毛发变亮特效（材质光泽度提升）
  - 满意表情（清洁后开心）
- **角色姿态**: 从抗拒到享受的转变
- **触发条件**: 用户选择清洁操作

#### Happy_Dance (开心舞蹈)
- **file_path**: `src/frontend/assets/animations/default/happy_dance.glb`
- **时长**: 8秒 (一次性播放)
- **动画内容**:
  - 跳跃旋转（连续3次跳跃加转圈）
  - 手臂挥舞（配合节奏摆动）
  - 开心大笑（夸张的面部表情）
  - 星星特效（粒子系统，围绕角色）
  - 结束pose（双手举高，胜利姿势）
- **角色姿态**: 极度兴奋，全身心投入
- **触发条件**: 吃饱且心情好时的特殊庆祝

#### Sick_Animation (生病状态)
- **file_path**: `src/frontend/assets/animations/default/sick_animation.glb`
- **时长**: 12秒循环
- **动画内容**:
  - 蜷缩躺下（缓慢倒地）
  - 咳嗽动作（身体前倾，手捂嘴）
  - 虚弱表情（脸色苍白，眼神无神）
  - 偶尔翻身（痛苦地改变姿势）
  - 体温升高效应（头部蒸汽粒子）
- **角色姿态**: 虚弱躺卧，无法站立
- **触发条件**: 长时间不照顾（所有状态 < 20）

#### Play_Seek (寻找注意)
- **file_path**: `src/frontend/assets/animations/default/play_seek.glb`
- **时长**: 6秒 (一次性播放)
- **动画内容**:
  - 跑向屏幕边缘（快速移动到边界）
  - 挥手动作（双臂大幅度摆动）
  - 期待表情（大眼睛，张望）
  - 跳跃吸引（在边缘处跳跃）
  - 返回原位（如果没有响应）
- **角色姿态**: 主动寻求互动，充满活力
- **触发条件**: 长时间无用户交互（>10分钟）

#### Sleep_Animation (睡觉动画)
- **file_path**: `src/frontend/assets/animations/default/sleep_animation.glb`
- **时长**: 5秒 (进入睡眠) + 循环睡眠动画
- **动画内容**:
  - 寻找位置（缓慢移动到舒适角落）
  - 躺下动作（蜷缩身体）
  - 盖被子（如果有被子配件）
  - 呼吸起伏（胸部规律起伏）
  - 偶尔翻身（睡眠中自然动作）
  - Zzz特效（头顶气泡）
- **角色姿态**: 完全放松的睡眠姿态
- **触发条件**: 夜间时间或体力值极低

## 4. 音频资源规格

### 4.1 音频通用规格
- **格式**: MP3 (兼容性好) + OGG (高质量)
- **采样率**: 44.1kHz
- **比特率**: 128kbps
- **声道**: 立体声

### 4.2 详细音频清单

#### 交互音效
- **caress_sound.mp3**: 抚摸时的呼噜声，2秒，温暖柔和
- **feed_sound.mp3**: 进食声音，3秒，咀嚼声+满足声
- **clean_sound.mp3**: 清洁音效，4秒，水流声+享受声
- **click_sound.mp3**: 点击反馈，0.5秒，清脆提示音

#### 状态音效
- **hungry_sound.mp3**: 饥饿提醒，3秒，虚弱咕噜声
- **happy_sound.mp3**: 开心声音，2秒，欢快叫声
- **tired_sound.mp3**: 疲惫声音，2秒，打哈欠声
- **sick_sound.mp3**: 生病声音，3秒，咳嗽+虚弱声

#### 环境音效
- **ambient_day.mp3**: 白天背景音，30秒循环，轻松音乐
- **ambient_night.mp3**: 夜间背景音，30秒循环，安静舒缓
- **celebration.mp3**: 庆祝音乐，10秒，欢快旋律

## 5. 纹理和材质规格

### 5.1 PBR材质参数
- **Base Color**: Albedo贴图，sRGB色彩空间
- **Metallic**: 金属度贴图，线性色彩空间，值范围0-1
- **Roughness**: 粗糙度贴图，线性色彩空间，值范围0-1
- **Normal**: 法线贴图，OpenGL格式，切线空间
- **Emissive**: 自发光贴图（用于特殊效果）

### 5.2 纹理分辨率
- **高配版**: 2048x2048
- **低配版**: 1024x1024
- **UI图标**: 512x512 (SVG优先)

### 5.3 特殊材质效果
- **毛发材质**: 使用各向异性反射，增加真实感
- **眼部材质**: 透明度+法线贴图，模拟湿润效果
- **动态材质**: 支持运行时参数调整（如清洁度影响光泽度）

## 6. 资源生成指导

### 6.1 AI生成提示词模板
对于每个动画，AI生成时使用以下模板：

**基础提示词**:
"3D cartoon pet character, cute and friendly, [具体动作描述], smooth animation, 30fps, GLB format, PBR materials, optimized for real-time rendering, loopable if applicable"

**示例 - Idle_Hungry**:
"3D cartoon pet character, cute and friendly, holding stomach with both hands, shivering slightly, looking anxious and hungry, occasional head turns toward viewer, smooth animation, 30fps, GLB format, PBR materials, optimized for real-time rendering, 6 second loop"

### 6.2 质量检查清单
- [ ] 动画流畅度 (无卡顿、突兀动作)
- [ ] 骨骼绑定正确 (无穿模、扭曲)
- [ ] 文件大小合理 (<5MB per GLB)
- [ ] 材质参数正确 (PBR workflow)
- [ ] 命名规范一致
- [ ] 循环动画无缝衔接