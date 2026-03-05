import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Cylinder } from '@react-three/drei'
import { BotState } from '../App'
import './BotAvatar.css'

interface BotAvatarProps {
  state: BotState
}

function CutePenguin({ state }: { state: BotState }) {
  const groupRef = useRef<THREE.Group>(null)
  const leftEyeRef = useRef<THREE.Mesh>(null)
  const rightEyeRef = useRef<THREE.Mesh>(null)
  const blushLeftRef = useRef<THREE.Mesh>(null)
  const blushRightRef = useRef<THREE.Mesh>(null)
  
  useFrame((_, delta) => {
    if (!groupRef.current) return
    
    // 待机动画 - 轻微摇摆
    if (state === 'idle') {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.001) * 0.1
      groupRef.current.position.y = Math.sin(Date.now() * 0.002) * 0.02
    }
    
    // 状态变化时的动画
    if (state === 'listening') {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.003) * 0.2
    }
    
    if (state === 'thinking') {
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.004) * 0.1
    }
    
    // 眼睛和脸颊颜色变化
    if (leftEyeRef.current && rightEyeRef.current) {
      const eyeColor = getEyeColor(state)
      ;(leftEyeRef.current.material as THREE.MeshStandardMaterial).emissive.set(eyeColor)
      ;(rightEyeRef.current.material as THREE.MeshStandardMaterial).emissive.set(eyeColor)
    }
    
    // 脸颊颜色变化
    if (blushLeftRef.current && blushRightRef.current) {
      const blushIntensity = getBlushIntensity(state)
      ;(blushLeftRef.current.material as THREE.MeshStandardMaterial).opacity = blushIntensity
      ;(blushRightRef.current.material as THREE.MeshStandardMaterial).opacity = blushIntensity
    }
  })

  const getEyeColor = (state: BotState): string => {
    switch (state) {
      case 'listening': return '#00ff88'
      case 'thinking': return '#ffaa00'
      case 'speaking': return '#4ecdc4'
      case 'error': return '#ff6b6b'
      default: return '#2d3748'
    }
  }

  const getBlushIntensity = (state: BotState): number => {
    switch (state) {
      case 'speaking': return 0.8
      case 'listening': return 0.6
      case 'thinking': return 0.4
      default: return 0.3
    }
  }

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* 身体 - 白色椭圆 */}
      <Sphere args={[1.2, 1.0, 1.6, 32, 32]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#ffffff" metalness={0.1} roughness={0.8} />
      </Sphere>
      
      {/* 背部 - 黑色半椭圆 */}
      <Sphere args={[1.4, 1.0, 1.8, 32, 32]} position={[0, 0, -0.1]}>
        <meshStandardMaterial color="#1a1a1a" metalness={0.2} roughness={0.7} side={THREE.BackSide} />
      </Sphere>
      
      {/* 头部 - 黑色圆形 */}
      <Sphere args={[0.8, 32, 32]} position={[0, 0.8, 0]}>
        <meshStandardMaterial color="#1a1a1a" metalness={0.2} roughness={0.7} />
      </Sphere>
      
      {/* 肚子 - 白色椭圆 */}
      <Sphere args={[0.9, 1.0, 1.2, 32, 32]} position={[0, -0.2, 0.1]}>
        <meshStandardMaterial color="#ffffff" metalness={0.1} roughness={0.8} />
      </Sphere>
      
      {/* 眼睛 - 白色眼白 */}
      <Sphere args={[0.18, 16, 16]} position={[-0.25, 1.1, 0.7]}>
        <meshStandardMaterial color="#ffffff" metalness={0.1} roughness={0.8} />
      </Sphere>
      <Sphere args={[0.18, 16, 16]} position={[0.25, 1.1, 0.7]}>
        <meshStandardMaterial color="#ffffff" metalness={0.1} roughness={0.8} />
      </Sphere>
      
      {/* 瞳孔 - 黑色 */}
      <Sphere ref={leftEyeRef} args={[0.08, 16, 16]} position={[-0.25, 1.1, 0.85]}>
        <meshStandardMaterial color="#2d3748" emissive="#2d3748" emissiveIntensity={0.5} />
      </Sphere>
      <Sphere ref={rightEyeRef} args={[0.08, 16, 16]} position={[0.25, 1.1, 0.85]}>
        <meshStandardMaterial color="#2d3748" emissive="#2d3748" emissiveIntensity={0.5} />
      </Sphere>
      
      {/* 脸颊 - 粉红色 */}
      <Sphere ref={blushLeftRef} args={[0.12, 16, 16]} position={[-0.4, 0.9, 0.8]}>
        <meshStandardMaterial color="#ff6b81" transparent opacity={0.3} />
      </Sphere>
      <Sphere ref={blushRightRef} args={[0.12, 16, 16]} position={[0.4, 0.9, 0.8]}>
        <meshStandardMaterial color="#ff6b81" transparent opacity={0.3} />
      </Sphere>
      
      {/* 嘴巴 - 橙色三角形 */}
      <Cone args={[0.15, 0.3, 4]} position={[0, 0.6, 0.9]} rotation={[0, 0, 0]}>
        <meshStandardMaterial color="#ff9f43" metalness={0.3} roughness={0.5} />
      </Cone>
      
      {/* 脚 - 橙色 */}
      <Cylinder args={[0.15, 0.15, 0.2, 8]} position={[-0.3, -1.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial color="#ff9f43" metalness={0.3} roughness={0.5} />
      </Cylinder>
      <Cylinder args={[0.15, 0.15, 0.2, 8]} position={[0.3, -1.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial color="#ff9f43" metalness={0.3} roughness={0.5} />
      </Cylinder>
      
      {/* 翅膀 - 黑色小椭圆 */}
      <Sphere args={[0.2, 0.8, 0.4, 16, 16]} position={[-0.8, -0.1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#1a1a1a" metalness={0.2} roughness={0.7} />
      </Sphere>
      <Sphere args={[0.2, 0.8, 0.4, 16, 16]} position={[0.8, -0.1, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <meshStandardMaterial color="#1a1a1a" metalness={0.2} roughness={0.7} />
      </Sphere>
    </group>
  )
}

export default function BotAvatar({ state }: BotAvatarProps) {
  return (
    <div className="bot-avatar-container">
      <Canvas camera={{ position: [0, 0, 4], fov: 45 }} style={{ background: 'transparent' }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#ffffff" />
        <pointLight position={[-5, -5, -5]} intensity={0.4} color="#ff9f43" />
        <CutePenguin state={state} />
      </Canvas>
      
      <div className="state-indicator">
        {getStateText(state)}
      </div>
    </div>
  )
}

function getStateText(state: BotState): string {
  switch (state) {
    case 'idle': return '🐧 待机中...'
    case 'listening': return '👂 我在听'
    case 'thinking': return '🤔 思考中...'
    case 'speaking': return '💬 说话中...'
    case 'error': return '😢 出错了'
    default: return ''
  }
}
