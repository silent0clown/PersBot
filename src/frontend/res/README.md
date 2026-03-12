# Blender宠物动画生成脚本使用说明

## 脚本功能

`generate_pet_animations.py` 是一个Blender Python脚本，用于自动生成PersBot项目所需的3D宠物动画资源。该脚本能够：

1. **自动建模**: 创建简单的柯基犬3D模型（身体、头部、尾巴）
2. **骨骼系统**: 自动生成完整的骨骼层级结构
3. **权重绑定**: 自动将模型部件绑定到对应骨骼
4. **动画生成**: 生成多种状态的动画序列
5. **批量导出**: 将所有动画导出为GLB格式文件

## 支持的动画类型

- `idle_normal.glb`: 普通待机动画（8秒循环，包含呼吸和尾巴摆动）
- `idle_hungry.glb`: 饥饿待机动画（6秒循环，包含摸肚子和身体发抖）
- `sleep_animation.glb`: 睡觉动画（5秒进入睡眠 + 循环呼吸）
- `sick_animation.glb`: 生病动画（12秒循环，包含蜷缩和咳嗽动作）

## 使用方法

### 1. 环境要求
- Blender 3.6 或更高版本
- Python 3.10+（Blender内置）

### 2. 命令行运行
```bash
# 在Blender安装目录下运行
blender --background --python generate_pet_animations.py
```

### 3. 参数说明
脚本目前不支持命令行参数，会自动生成所有四种动画类型。

如果需要生成特定动画，可以修改脚本中的`main()`函数：
```python
def main():
    # 只生成饥饿动画
    animations = ["idle_hungry"]
    
    # 或者生成指定的动画列表
    animations = ["idle_normal", "sleep"]
```

### 4. 输出路径
生成的GLB文件将保存在脚本同级目录下的`models/`文件夹中：
```
res/
├── generate_pet_animations.py
├── README.md
└── models/
    ├── idle_normal.glb
    ├── idle_hungry.glb
    ├── sleep_animation.glb
    └── sick_animation.glb
```

## 扩展开发

### 添加新动画类型
1. 在脚本中创建新的动画函数（参考现有函数格式）
2. 在`generate_animation()`函数中添加新的elif分支
3. 在`main()`函数的animations列表中添加新动画名称

### 自定义模型参数
修改以下函数中的参数来调整模型外观：
- `create_corgi_model()`: 调整身体、头部、尾巴的尺寸和位置
- `create_armature()`: 调整骨骼结构和长度
- 各动画函数: 调整关键帧位置、旋转角度和时间长度

## 注意事项

1. **Blender专用**: 此脚本只能在Blender环境中运行，不能作为普通Python脚本执行
2. **内存占用**: 生成多个动画时会占用较多内存，建议逐个生成或增加系统内存
3. **模型简化**: 当前模型使用基础几何体，如需更复杂模型需要手动建模后修改绑定逻辑
4. **动画质量**: 自动生成的动画较为基础，复杂动画仍需手动调整关键帧

## 故障排除

**问题**: 运行时出现"Import bpy could not be resolved"
**解决**: 这是正常现象，因为bpy模块只在Blender内部可用，不影响实际运行

**问题**: 导出文件为空或损坏
**解决**: 
- 确保Blender版本兼容
- 检查是否有足够的磁盘空间
- 验证模型和骨骼是否正确创建

**问题**: 动画播放不流畅
**解决**: 
- 调整关键帧间隔
- 增加动画帧数
- 检查骨骼绑定是否正确