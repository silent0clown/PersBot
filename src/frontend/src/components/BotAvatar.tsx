import { useRef, useState, useEffect, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Cylinder, Cone, Box } from '@react-three/drei'
import * as THREE from 'three'
import { BotState } from '../App'
import './BotAvatar.css'

interface BotAvatarProps {
  state: BotState
}

// 颜色方案
const COLORS = {
  body: '#1a1a1a',        // 黑色身体
  belly: '#ffffff',       // 白色肚子
  bow: '#ff9fc9',         // 粉色蝴蝶结
  bowCenter: '#ff85bb',   // 深粉色蝴蝶结中心
  beak: '#ff8c42',        // 橙色嘴巴
  feet: '#ff9d5c',        // 橙色脚掌
  eyeWhite: '#ffffff',    // 白色眼白
  pupil: '#1a1a1a',       // 黑色瞳孔
  blush: '#ffb3c6'        // 粉色腮红
}

// 粉色蝴蝶结组件
function PinkBow({ state }: { state: BotState }) {
  const bowRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (!bowRef.current) return

    // listening 状态下快速摆动
    if (state === 'listening') {
      bowRef.current.rotation.z = Math.sin(Date.now() * 0.008) * 0.3
    } else {
      // 其他状态轻微摆动
      bowRef.current.rotation.z = Math.sin(Date.now() * 0.002) * 0.1
    }
  })

  return (
    <group ref={bowRef} position={[0.35, 1.3, 0.2]}>
      {/* 左侧蝴蝶结 */}
      <Sphere args={[0.22, 16, 16]} position={[-0.18, 0, 0]} scale={[1, 0.8, 0.5]}>
        <meshStandardMaterial
          color={COLORS.bow}
          metalness={0.1}
          roughness={0.4}
          emissive={COLORS.bow}
          emissiveIntensity={0.2}
        />
      </Sphere>

      {/* 右侧蝴蝶结 */}
      <Sphere args={[0.22, 16, 16]} position={[0.18, 0, 0]} scale={[1, 0.8, 0.5]}>
        <meshStandardMaterial
          color={COLORS.bow}
          metalness={0.1}
          roughness={0.4}
          emissive={COLORS.bow}
          emissiveIntensity={0.2}
        />
      </Sphere>

      {/* 中心结 */}
      <Box args={[0.18, 0.18, 0.15]}>
        <meshStandardMaterial
          color={COLORS.bowCenter}
          metalness={0.1}
          roughness={0.4}
        />
      </Box>

      {/* 下垂的丝带 */}
      <Box args={[0.08, 0.25, 0.06]} position={[-0.08, -0.2, 0]} rotation={[0, 0, 0.2]}>
        <meshStandardMaterial color={COLORS.bow} metalness={0.1} roughness={0.4} />
      </Box>
      <Box args={[0.08, 0.25, 0.06]} position={[0.08, -0.2, 0]} rotation={[0, 0, -0.2]}>
        <meshStandardMaterial color={COLORS.bow} metalness={0.1} roughness={0.4} />
      </Box>
    </group>
  )
}

// 眼睛组件
function Eye({ position, state }: { position: [number, number, number], state: BotState }) {
  const pupilRef = useRef<THREE.Mesh>(null)
  const [blinkScale, setBlinkScale] = useState(1)

  // 眨眼动画
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlinkScale(0.1)
      setTimeout(() => setBlinkScale(1), 150)
    }, 3000 + Math.random() * 2000) // 随机间隔

    return () => clearInterval(blinkInterval)
  }, [])

  // 眼睛状态颜色
  useFrame(() => {
    if (!pupilRef.current) return

    const eyeColor = getEyeColor(state)
    ;(pupilRef.current.material as THREE.MeshStandardMaterial).emissive.set(eyeColor)

    // thinking 状态眼睛上下移动
    if (state === 'thinking') {
      pupilRef.current.position.y = Math.sin(Date.now() * 0.003) * 0.05
    } else {
      pupilRef.current.position.y = 0
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

  return (
    <group position={position}>
      {/* 眼白 */}
      <Sphere args={[0.2, 16, 16]} scale={[1, blinkScale, 1]}>
        <meshStandardMaterial
          color={COLORS.eyeWhite}
          metalness={0.05}
          roughness={0.3}
        />
      </Sphere>

      {/* 瞳孔 */}
      <Sphere ref={pupilRef} args={[0.09, 16, 16]} position={[0, 0, 0.18]}>
        <meshStandardMaterial
          color={COLORS.pupil}
          emissive="#2d3748"
          emissiveIntensity={0.5}
          metalness={0.2}
          roughness={0.6}
        />
      </Sphere>

      {/* 高光 */}
      <Sphere args={[0.045, 8, 8]} position={[0.06, 0.06, 0.22]}>
        <meshStandardMaterial
          color={COLORS.eyeWhite}
          emissive={COLORS.eyeWhite}
          emissiveIntensity={2}
        />
      </Sphere>
    </group>
  )
}

// 嘴巴组件
function Beak({ state }: { state: BotState }) {
  const beakRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (!beakRef.current) return

    // speaking 状态嘴巴开合动画
    if (state === 'speaking') {
      const openAmount = Math.abs(Math.sin(Date.now() * 0.008)) * 0.15
      beakRef.current.rotation.x = openAmount
    } else {
      beakRef.current.rotation.x = 0
    }
  })

  return (
    <group ref={beakRef} position={[0, 0.85, 0.85]}>
      {/* 上嘴 */}
      <Cone args={[0.18, 0.35, 4]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial
          color={COLORS.beak}
          metalness={0.2}
          roughness={0.5}
        />
      </Cone>

      {/* 下嘴 */}
      <Cone args={[0.15, 0.28, 4]} position={[0, -0.08, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <meshStandardMaterial
          color={COLORS.beak}
          metalness={0.2}
          roughness={0.5}
        />
      </Cone>
    </group>
  )
}

// 脚掌组件
function Feet() {
  const leftFootRef = useRef<THREE.Mesh>(null)
  const rightFootRef = useRef<THREE.Mesh>(null)

  useFrame(() => {
    if (!leftFootRef.current || !rightFootRef.current) return

    // 轻微的左右摇摆
    const wobble = Math.sin(Date.now() * 0.002) * 0.05
    leftFootRef.current.rotation.y = wobble
    rightFootRef.current.rotation.y = -wobble
  })

  return (
    <>
      {/* 左脚 */}
      <Sphere ref={leftFootRef} args={[0.25, 16, 16]} position={[-0.35, -1.4, 0.15]} scale={[1.2, 0.5, 1.8]}>
        <meshStandardMaterial
          color={COLORS.feet}
          metalness={0.2}
          roughness={0.6}
        />
      </Sphere>

      {/* 右脚 */}
      <Sphere ref={rightFootRef} args={[0.25, 16, 16]} position={[0.35, -1.4, 0.15]} scale={[1.2, 0.5, 1.8]}>
        <meshStandardMaterial
          color={COLORS.feet}
          metalness={0.2}
          roughness={0.6}
        />
      </Sphere>
    </>
  )
}

// 翅膀组件
function Wings() {
  const leftWingRef = useRef<THREE.Mesh>(null)
  const rightWingRef = useRef<THREE.Mesh>(null)

  useFrame(() => {
    if (!leftWingRef.current || !rightWingRef.current) return

    // 轻微摆动
    const swing = Math.sin(Date.now() * 0.002) * 0.15
    leftWingRef.current.rotation.z = Math.PI / 6 + swing
    rightWingRef.current.rotation.z = -Math.PI / 6 - swing
  })

  return (
    <>
      {/* 左翅膀 */}
      <Sphere ref={leftWingRef} args={[0.3, 16, 16]} position={[-0.95, 0.2, 0]} scale={[0.6, 1.2, 0.4]}>
        <meshStandardMaterial
          color={COLORS.body}
          metalness={0.15}
          roughness={0.6}
        />
      </Sphere>

      {/* 右翅膀 */}
      <Sphere ref={rightWingRef} args={[0.3, 16, 16]} position={[0.95, 0.2, 0]} scale={[0.6, 1.2, 0.4]}>
        <meshStandardMaterial
          color={COLORS.body}
          metalness={0.15}
          roughness={0.6}
        />
      </Sphere>
    </>
  )
}

// 腮红组件
function Blush({ state }: { state: BotState }) {
  const blushLeftRef = useRef<THREE.Mesh>(null)
  const blushRightRef = useRef<THREE.Mesh>(null)

  useFrame(() => {
    if (!blushLeftRef.current || !blushRightRef.current) return

    const intensity = getBlushIntensity(state)
    ;(blushLeftRef.current.material as THREE.MeshStandardMaterial).opacity = intensity
    ;(blushRightRef.current.material as THREE.MeshStandardMaterial).opacity = intensity
  })

  const getBlushIntensity = (state: BotState): number => {
    switch (state) {
      case 'speaking': return 0.7
      case 'listening': return 0.6
      case 'thinking': return 0.4
      default: return 0.35
    }
  }

  return (
    <>
      <Sphere ref={blushLeftRef} args={[0.15, 16, 16]} position={[-0.55, 0.85, 0.75]}>
        <meshStandardMaterial
          color={COLORS.blush}
          transparent
          opacity={0.35}
          metalness={0.1}
          roughness={0.8}
        />
      </Sphere>
      <Sphere ref={blushRightRef} args={[0.15, 16, 16]} position={[0.55, 0.85, 0.75]}>
        <meshStandardMaterial
          color={COLORS.blush}
          transparent
          opacity={0.35}
          metalness={0.1}
          roughness={0.8}
        />
      </Sphere>
    </>
  )
}

// 主企鹅组件
function CutePenguin({ state }: { state: BotState }) {
  const groupRef = useRef<THREE.Group>(null)
  const [breathScale, setBreathScale] = useState(1)

  // 呼吸和动画
  useFrame(() => {
    if (!groupRef.current) return

    // 呼吸效果
    const breath = 1 + Math.sin(Date.now() * 0.0015) * 0.02
    setBreathScale(breath)

    // 状态动画
    if (state === 'idle') {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.001) * 0.08
      groupRef.current.position.y = Math.sin(Date.now() * 0.002) * 0.03
    } else if (state === 'listening') {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.004) * 0.15
    } else if (state === 'thinking') {
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.003) * 0.08
      groupRef.current.rotation.z = Math.sin(Date.now() * 0.002) * 0.05
    } else if (state === 'speaking') {
      groupRef.current.position.y = Math.sin(Date.now() * 0.005) * 0.05
    }
  })

  return (
    <group ref={groupRef} scale={breathScale}>
      {/* 身体 - 更圆润的黑色球形 */}
      <Sphere args={[1.0, 32, 32]} position={[0, 0, 0]} scale={[1.1, 1.2, 1.05]}>
        <meshStandardMaterial
          color={COLORS.body}
          metalness={0.08}
          roughness={0.6}
          envMapIntensity={0.4}
        />
      </Sphere>

      {/* 肚子 - 更大的白色区域 */}
      <Sphere args={[0.85, 32, 32]} position={[0, -0.1, 0.45]} scale={[1, 1.15, 0.8]}>
        <meshStandardMaterial
          color={COLORS.belly}
          metalness={0.05}
          roughness={0.7}
        />
      </Sphere>

      {/* 头部 - 黑色圆形 */}
      <Sphere args={[0.75, 32, 32]} position={[0, 1.0, 0]}>
        <meshStandardMaterial
          color={COLORS.body}
          metalness={0.08}
          roughness={0.6}
          envMapIntensity={0.4}
        />
      </Sphere>

      {/* 面部白色区域 */}
      <Sphere args={[0.6, 32, 32]} position={[0, 0.95, 0.35]} scale={[0.95, 1, 0.7]}>
        <meshStandardMaterial
          color={COLORS.belly}
          metalness={0.05}
          roughness={0.7}
        />
      </Sphere>

      {/* 粉色蝴蝶结 - 标志性元素 */}
      <PinkBow state={state} />

      {/* 眼睛 */}
      <Eye position={[-0.28, 1.15, 0.65]} state={state} />
      <Eye position={[0.28, 1.15, 0.65]} state={state} />

      {/* 嘴巴 */}
      <Beak state={state} />

      {/* 脚掌 */}
      <Feet />

      {/* 翅膀 */}
      <Wings />

      {/* 腮红 */}
      <Blush state={state} />
    </group>
  )
}

export default function BotAvatar({ state }: BotAvatarProps) {
  return (
    <div className="bot-avatar-container">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }} style={{ background: 'transparent' }}>
        {/* 增强的光照系统 */}
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color="#ffffff" />
        <pointLight position={[0, 3, 3]} intensity={0.6} color="#ffc9e5" />
        <pointLight position={[-3, 0, 2]} intensity={0.4} color="#ff9fc9" />
        <spotLight position={[3, 3, 3]} intensity={0.5} angle={0.3} penumbra={0.5} />

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
