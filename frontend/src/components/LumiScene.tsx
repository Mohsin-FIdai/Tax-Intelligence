"use client"
import { Canvas, useFrame } from '@react-three/fiber'
import { useGLTF, useAnimations } from '@react-three/drei'
import { useEffect, useRef, Suspense, useState, useCallback } from 'react'
import * as THREE from 'three'

function LumiModel({ isThinking }: { isThinking: boolean }) {
  const group = useRef<THREE.Group>(null!)
  const { scene, animations } = useGLTF('/models/lumi-character.glb')
  const { actions, names } = useAnimations(animations, group)
  const prevAnim = useRef('Idle')

  // Play idle animation on mount
  useEffect(() => {
    if (names.length > 0) {
      console.log('3D Model loaded! Animations:', names)
      // Find and play idle
      const idleName = names.find(n => n === 'Idle') || names[0]
      const idle = actions[idleName]
      if (idle) {
        idle.reset().fadeIn(0.5).play()
        prevAnim.current = idleName
      }
    }
  }, [actions, names])

  // Switch animations based on isThinking
  useEffect(() => {
    if (names.length === 0) return
    const thinkName = names.find(n => n === 'Wave') || names.find(n => n === 'ThumbsUp') || names.find(n => n === 'Yes') || names[1]
    const idleName = names.find(n => n === 'Idle') || names[0]
    const targetAnim = isThinking ? thinkName : idleName
    if (!targetAnim || targetAnim === prevAnim.current) return

    const prev = actions[prevAnim.current]
    const next = actions[targetAnim]
    if (prev) prev.fadeOut(0.4)
    if (next) {
      next.reset().fadeIn(0.4).play()
      prevAnim.current = targetAnim
    }
  }, [isThinking, actions, names])

  // Gentle floating + rotation
  useFrame((state) => {
    if (group.current) {
      group.current.position.y = -1 + Math.sin(state.clock.elapsedTime * 0.8) * 0.06
      group.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.12
    }
  })

  // Recolor materials to match Lumi's teal/navy palette
  useEffect(() => {
    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        materials.forEach((mat) => {
          if (mat && 'color' in mat) {
            const stdMat = mat as THREE.MeshStandardMaterial
            const hsl = { h: 0, s: 0, l: 0 }
            stdMat.color.getHSL(hsl)
            if (hsl.l > 0.6) {
              stdMat.color.setHSL(0.48, 0.2, Math.min(hsl.l, 0.9))
            } else if (hsl.l > 0.3) {
              stdMat.color.setHSL(0.52, 0.5, hsl.l)
            } else {
              stdMat.color.setHSL(0.55, 0.7, 0.2)
            }
            stdMat.emissive = new THREE.Color(0x0d9488)
            stdMat.emissiveIntensity = 0.08
            stdMat.needsUpdate = true
          }
        })
      }
    })
  }, [scene])

  return (
    <group ref={group} position={[0, -1, 0]} scale={0.85}>
      <primitive object={scene} />
    </group>
  )
}

useGLTF.preload('/models/lumi-character.glb')

function FallbackImage() {
  return null
}

export default function LumiScene({ isThinking = false }: { isThinking?: boolean }) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <img src="/lumi-3d.png" alt="Lumi" className="w-full h-full object-contain" 
          style={{ animation: 'float-complex 6s ease-in-out infinite' }} />
      </div>
    )
  }

  return (
    <Canvas
      camera={{ position: [0, 0.2, 3], fov: 40 }}
      style={{ width: '100%', height: '100%' }}
      gl={{ alpha: true, antialias: true, powerPreference: 'default' }}
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0)
      }}
      onError={() => setHasError(true)}
    >
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} color="#ffffff" />
      <directionalLight position={[-3, 3, 2]} intensity={0.5} color="#2dd4bf" />
      <pointLight position={[0, 2, 3]} intensity={0.6} color="#0d9488" />
      <spotLight position={[0, 5, 0]} intensity={0.3} angle={0.5} penumbra={1} color="#818cf8" />

      <Suspense fallback={<FallbackImage />}>
        <LumiModel isThinking={isThinking} />
      </Suspense>
    </Canvas>
  )
}