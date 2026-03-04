import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Cylinder } from '@react-three/drei'
import { BotState } from '../App'
import './BotAvatar.css'

interface BotAvatarProps {
  state: BotState
}

function Robot({ state }: BotState) {
  const groupRef = useRef<THREE.Group>(null)
  const leftEyeRef = useRef<THREE.Mesh>(null)
  const rightEyeRef = useRef<THREE.Mesh>(null)
  
  useFrame((_, delta) => {
    if (!groupRef.current) return
    
    // 待机呼吸动画
    if (state === 'idle') {
      groupRef.current.position.y = Math.sin(Date.now() * 0.001) * 0.05
    }
    
    // 眼睛动画
    if (leftEyeRef.current && rightEyeRef.current) {
      const eyeColor = getEyeColor(state)
      ;(leftEyeRef.current.material as THREE.MeshStandardMaterial).emissive.set(eyeColor)
      ;(rightEyeRef.current.material as THREE.MeshStandardMaterial).emissive.set(eyeColor)
    }
  })

  const getEyeColor = (state: BotState): string => {
    switch (state) {
      case 'listening': return '#00ff88'
      case 'thinking': return '#ffaa00'
      case 'speaking': return '#00aaff'
      case 'error': return '#ff4444'
      default: return '#4f46e5'
    }
  }

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* 头部 */}
      <Sphere args={[1, 32, 32]} position={[0, 1.2, 0]}>
        <meshStandardMaterial color="#e0e7ff" metalness={0.3} roughness={0.4} />
      </Sphere>
      
      {/* 眼睛 */}
      <Sphere ref={leftEyeRef} args={[0.15, 16, 16]} position={[-0.3, 1.3, 0.85]}>
        <meshStandardMaterial color="#4f46e5" emissive="#4f46e5" emissiveIntensity={0.5} />
      </Sphere>
      <Sphere ref={rightEyeRef} args={[0.15, 16, 16]} position={[0.3, 1.3, 0.85]}>
        <meshStandardMaterial color="#4f46e5" emissive="#4f46e5" emissiveIntensity={0.5} />
      </Sphere>
      
      {/* 身体 */}
      <Cylinder args={[0.6, 0.8, 1.2, 32]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#c7d2fe" metalness={0.3} roughness={0.4} />
      </Cylinder>
      
      {/* 底座 */}
      <Cylinder args={[0.7, 0.9, 0.3, 32]} position={[0, -0.75, 0]}>
        <meshStandardMaterial color="#6366f1" metalness={0.5} roughness={0.3} />
      </Cylinder>
      
      {/* 触角 */}
      <Cylinder args={[0.03, 0.03, 0.3, 8]} position={[0, 2.3, 0]}>
        <meshStandardMaterial color="#6366f1" />
      </Cylinder>
      <Sphere args={[0.08, 16, 16]} position={[0, 2.45, 0]}>
        <meshStandardMaterial color="#f472b6" emissive="#f472b6" emissiveIntensity={0.3} />
      </Sphere>
    </group>
  )
}

export default function BotAvatar({ state }: BotAvatarProps) {
  return (
    <div className="bot-avatar-container">
      <Canvas camera={{ position: [0, 1, 4], fov: 50 }} style={{ background: 'transparent' }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.3} color="#6366f1" />
        <Robot state={state} />
      </Canvas>
      
      <div className="state-indicator">
        {getStateText(state)}
      </div>
    </div>
  )
}

function getStateText(state: BotState): string {
  switch (state) {
    case 'idle': return '待机中...'
    case 'listening': return '我在听'
    case 'thinking': return '思考中...'
    case 'speaking': return '说话中...'
    case 'error': return '出错了'
    default: return ''
  }
}
