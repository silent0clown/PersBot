import { useRef, useEffect, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGLTF, Environment } from '@react-three/drei'
import { BotState } from '../App'
import { fitModelToView } from '../utils/modelUtils'
import './BotAvatar.css'

interface GLBPetProps {
  state: BotState
}

// GLB宠物模型组件
function GLBPet({ state }: GLBPetProps) {
  const modelRef = useRef<THREE.Group>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // 使用drei的useGLTF hook加载GLB模型
  const { scene: glbModel, error: loadError } = useGLTF('/res/models/dog/dog_model.glb')
  
  // 处理加载状态和错误
  useEffect(() => {
    if (loadError) {
      setError('模型加载失败: ' + loadError.message)
      setLoading(false)
      return
    }
    
    if (!glbModel) return
    
    try {
      // 调整模型大小和位置
      fitModelToView(glbModel)
      
      // 设置材质属性
      glbModel.traverse((child: any) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh
          if (mesh.material) {
            if (Array.isArray(mesh.material)) {
              mesh.material.forEach((material: THREE.Material) => {
                if ((material as THREE.MeshStandardMaterial).metalness !== undefined) {
                  (material as THREE.MeshStandardMaterial).metalness = 0.1
                  ;(material as THREE.MeshStandardMaterial).roughness = 0.7
                  ;(material as THREE.MeshStandardMaterial).envMapIntensity = 0.3
                }
              })
            } else {
              if ((mesh.material as THREE.MeshStandardMaterial).metalness !== undefined) {
                (mesh.material as THREE.MeshStandardMaterial).metalness = 0.1
                ;(mesh.material as THREE.MeshStandardMaterial).roughness = 0.7
                ;(mesh.material as THREE.MeshStandardMaterial).envMapIntensity = 0.3
              }
            }
          }
        }
      })
      
      setLoading(false)
    } catch (err) {
      setError('模型处理失败: ' + (err as Error).message)
      setLoading(false)
    }
    
  }, [glbModel, loadError])

  // 动画和状态响应
  useFrame(() => {
    if (!modelRef.current) return

    // 基础呼吸动画
    const breath = 1 + Math.sin(Date.now() * 0.0015) * 0.02
    modelRef.current.scale.setScalar(breath)

    // 根据状态应用不同动画
    switch (state) {
      case 'idle':
        modelRef.current.rotation.y = Math.sin(Date.now() * 0.001) * 0.08
        break
      case 'listening':
        modelRef.current.rotation.y = Math.sin(Date.now() * 0.004) * 0.15
        break
      case 'thinking':
        modelRef.current.rotation.x = Math.sin(Date.now() * 0.003) * 0.08
        modelRef.current.rotation.z = Math.sin(Date.now() * 0.002) * 0.05
        break
      case 'speaking':
        modelRef.current.position.y = Math.sin(Date.now() * 0.005) * 0.05
        break
      default:
        modelRef.current.rotation.set(0, 0, 0)
        modelRef.current.position.y = 0
    }
  })

  if (loading) return null
  
  if (error) {
    console.error('GLB Model Error:', error)
    return null
  }
  
  if (!glbModel) return null

  return (
    <group ref={modelRef}>
      <primitive object={glbModel} />
    </group>
  )
}

interface BotAvatarProps {
  state: BotState
}

export default function BotAvatar({ state }: BotAvatarProps) {
  return (
    <div className="bot-avatar-container">
      <Canvas 
        camera={{ position: [0, 0, 3], fov: 50 }} 
        style={{ 
          background: 'transparent',
          width: '100%',
          height: '100%'
        }}
        shadows
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
      >
        {/* 光照系统 */}
        <ambientLight intensity={0.6} />
        <directionalLight 
          position={[5, 5, 5]} 
          intensity={1.0} 
          color="#ffffff" 
          castShadow
        />
        <pointLight position={[0, 3, 3]} intensity={0.5} color="#ffffff" />
        <hemisphereLight intensity={0.2} groundColor="#444444" />
        
        {/* 环境贴图 - 移除网络依赖，使用本地光照 */}

        {/* GLB宠物模型 */}
        <GLBPet state={state} />
      </Canvas>

      <div className="state-indicator">
        {getStateText(state)}
      </div>
    </div>
  )
}

function getStateText(state: BotState): string {
  switch (state) {
    case 'idle': return '🐶 待机中...'
    case 'listening': return '👂 我在听'
    case 'thinking': return '🤔 思考中...'
    case 'speaking': return '💬 说话中...'
    case 'error': return '😢 出错了'
    default: return ''
  }
}