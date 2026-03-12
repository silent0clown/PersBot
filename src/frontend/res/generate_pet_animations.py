import bpy
import math
import os

def clear_scene():
    """清空当前场景"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_scene():
    """设置场景参数"""
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.unit_settings.system = 'METRIC'
    scene.frame_start = 1

def create_corgi_model():
    """创建柯基模型"""
    # 创建身体
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.1))
    body = bpy.context.object
    body.name = "body"
    body.scale = (0.11, 0.05, 0.05)
    
    # 创建头部
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0.14, 0, 0.12))
    head = bpy.context.object
    head.name = "head"
    
    # 创建尾巴
    bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.12, location=(-0.12, 0, 0.13))
    tail = bpy.context.object
    tail.name = "tail"
    tail.rotation_euler[1] = math.radians(90)
    
    return body, head, tail

def create_armature():
    """创建骨骼系统"""
    bpy.ops.object.armature_add(location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "Pet_Armature"
    
    bpy.ops.object.mode_set(mode='EDIT')
    bones = arm.data.edit_bones
    
    # 清除默认骨骼
    bones.remove(bones[0])
    
    # 创建根骨骼
    root = bones.new("root")
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.2)
    
    # 创建脊柱骨骼
    spine = bones.new("spine")
    spine.head = (0, 0, 0.1)
    spine.tail = (0.1, 0, 0.15)
    spine.parent = root
    
    # 创建颈部骨骼
    neck = bones.new("neck")
    neck.head = (0.1, 0, 0.15)
    neck.tail = (0.14, 0, 0.18)
    neck.parent = spine
    
    # 创建头部骨骼
    head_bone = bones.new("head")
    head_bone.head = (0.14, 0, 0.18)
    head_bone.tail = (0.18, 0, 0.2)
    head_bone.parent = neck
    
    # 创建尾巴骨骼
    tail_bone = bones.new("tail")
    tail_bone.head = (-0.1, 0, 0.14)
    tail_bone.tail = (-0.18, 0, 0.16)
    tail_bone.parent = spine
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm

def assign_vertex_groups(obj, bone_name):
    """为对象分配顶点组"""
    if bone_name not in obj.vertex_groups:
        obj.vertex_groups.new(name=bone_name)
    vg = obj.vertex_groups[bone_name]
    vg.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')

def bind_model_to_armature(body, head, tail, armature):
    """绑定模型到骨骼"""
    # 分配顶点组
    assign_vertex_groups(body, "spine")
    assign_vertex_groups(head, "head")
    assign_vertex_groups(tail, "tail")
    
    # 设置父级
    for obj in [body, head, tail]:
        obj.select_set(True)
    
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type='ARMATURE')

def create_idle_normal_animation(armature, duration_frames=240):
    """创建普通待机动画 (8秒)"""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    scene = bpy.context.scene
    scene.frame_end = duration_frames
    
    # 呼吸动画 (脊柱上下移动)
    spine_bone = armature.pose.bones["spine"]
    spine_bone.location[2] = 0
    spine_bone.keyframe_insert(data_path="location", frame=1)
    spine_bone.location[2] = 0.005
    spine_bone.keyframe_insert(data_path="location", frame=120)
    spine_bone.location[2] = 0
    spine_bone.keyframe_insert(data_path="location", frame=240)
    
    # 尾巴摆动
    tail_bone = armature.pose.bones["tail"]
    tail_bone.rotation_euler[2] = math.radians(-15)
    tail_bone.keyframe_insert(data_path="rotation_euler", frame=1)
    tail_bone.rotation_euler[2] = math.radians(15)
    tail_bone.keyframe_insert(data_path="rotation_euler", frame=120)
    tail_bone.rotation_euler[2] = math.radians(-15)
    tail_bone.keyframe_insert(data_path="rotation_euler", frame=240)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def create_idle_hungry_animation(armature, duration_frames=180):
    """创建饥饿待机动画 (6秒)"""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    scene = bpy.context.scene
    scene.frame_end = duration_frames
    
    # 频繁摸肚子 (脊柱前后移动模拟手部动作)
    spine_bone = armature.pose.bones["spine"]
    for i in range(0, duration_frames + 1, 60):  # 每2秒一次
        frame = i
        spine_bone.location[1] = 0
        spine_bone.keyframe_insert(data_path="location", frame=frame)
        spine_bone.location[1] = -0.02
        spine_bone.keyframe_insert(data_path="location", frame=frame + 15)
        spine_bone.location[1] = 0
        spine_bone.keyframe_insert(data_path="location", frame=frame + 30)
    
    # 身体发抖 (高频小幅度震动)
    for frame in range(1, duration_frames + 1, 5):
        shake_amount = 0.002 * math.sin(frame * 0.5)
        spine_bone.location[2] = shake_amount
        spine_bone.keyframe_insert(data_path="location", frame=frame)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def create_sleep_animation(armature, duration_frames=150):
    """创建睡觉动画 (5秒进入睡眠 + 循环)"""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    scene = bpy.context.scene
    scene.frame_end = duration_frames
    
    # 躺下动作
    spine_bone = armature.pose.bones["spine"]
    neck_bone = armature.pose.bones["neck"]
    head_bone = armature.pose.bones["head"]
    
    # 初始站立
    spine_bone.location[2] = 0.1
    neck_bone.rotation_euler[0] = 0
    head_bone.rotation_euler[0] = 0
    spine_bone.keyframe_insert(data_path="location", frame=1)
    neck_bone.keyframe_insert(data_path="rotation_euler", frame=1)
    head_bone.keyframe_insert(data_path="rotation_euler", frame=1)
    
    # 躺下
    spine_bone.location[2] = 0.02
    neck_bone.rotation_euler[0] = math.radians(-30)
    head_bone.rotation_euler[0] = math.radians(-30)
    spine_bone.keyframe_insert(data_path="location", frame=90)
    neck_bone.keyframe_insert(data_path="rotation_euler", frame=90)
    head_bone.keyframe_insert(data_path="rotation_euler", frame=90)
    
    # 呼吸起伏
    for i in range(90, duration_frames + 1, 30):
        frame = i
        spine_bone.location[2] = 0.02 + 0.003
        spine_bone.keyframe_insert(data_path="location", frame=frame)
        spine_bone.location[2] = 0.02
        spine_bone.keyframe_insert(data_path="location", frame=frame + 15)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def create_sick_animation(armature, duration_frames=360):
    """创建生病动画 (12秒循环)"""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    scene = bpy.context.scene
    scene.frame_end = duration_frames
    
    spine_bone = armature.pose.bones["spine"]
    neck_bone = armature.pose.bones["neck"]
    head_bone = armature.pose.bones["head"]
    
    # 蜷缩躺下
    spine_bone.location[2] = 0.02
    neck_bone.rotation_euler[0] = math.radians(-45)
    head_bone.rotation_euler[0] = math.radians(-45)
    spine_bone.keyframe_insert(data_path="location", frame=1)
    neck_bone.keyframe_insert(data_path="rotation_euler", frame=1)
    head_bone.keyframe_insert(data_path="rotation_euler", frame=1)
    
    # 咳嗽动作 (每60帧一次，共6次)
    for cough_time in [60, 120, 180, 240, 300, 360]:
        # 咳嗽前准备
        spine_bone.location[2] = 0.03
        spine_bone.keyframe_insert(data_path="location", frame=cough_time - 10)
        # 咳嗽动作
        spine_bone.location[2] = 0.01
        spine_bone.keyframe_insert(data_path="location", frame=cough_time)
        # 恢复
        spine_bone.location[2] = 0.02
        spine_bone.keyframe_insert(data_path="location", frame=cough_time + 10)
    
    bpy.ops.object.mode_set(mode='OBJECT')

def export_glb(filepath):
    """导出GLB文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        export_animations=True,
        export_yup=True,
        export_apply=True
    )

def generate_animation(animation_type):
    """生成指定类型的动画"""
    clear_scene()
    setup_scene()
    
    body, head, tail = create_corgi_model()
    armature = create_armature()
    bind_model_to_armature(body, head, tail, armature)
    
    if animation_type == "idle_normal":
        create_idle_normal_animation(armature)
        export_glb("models/idle_normal.glb")
    elif animation_type == "idle_hungry":
        create_idle_hungry_animation(armature)
        export_glb("models/idle_hungry.glb")
    elif animation_type == "sleep":
        create_sleep_animation(armature)
        export_glb("models/sleep_animation.glb")
    elif animation_type == "sick":
        create_sick_animation(armature)
        export_glb("models/sick_animation.glb")
    else:
        print(f"Unknown animation type: {animation_type}")

def main():
    """主函数 - 生成所有动画"""
    animations = ["idle_normal", "idle_hungry", "sleep", "sick"]
    
    for anim in animations:
        print(f"Generating {anim} animation...")
        generate_animation(anim)
    
    print("All animations generated successfully!")

if __name__ == "__main__":
    main()