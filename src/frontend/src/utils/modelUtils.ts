// src/frontend/src/utils/modelUtils.ts
import * as THREE from 'three'

export function fitModelToView(model: THREE.Group) {
  // 计算模型的包围盒
  const box = new THREE.Box3().setFromObject(model)
  const size = box.getSize(new THREE.Vector3())
  
  // 计算合适的缩放因子
  const maxDim = Math.max(size.x, size.y, size.z)
  const scale = 2 / maxDim // 调整这个值来控制模型大小
  
  // 应用缩放
  model.scale.set(scale, scale, scale)
  
  // 居中模型
  const center = box.getCenter(new THREE.Vector3())
  const offset = center.clone().multiplyScalar(-scale)
  model.position.copy(offset)
  
  return { scale, offset }
}