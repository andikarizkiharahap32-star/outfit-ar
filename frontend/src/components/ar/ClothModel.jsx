// ClothModel.jsx
// Komponen React Three Fiber untuk baju rigged dengan:
// - Texture swapping yang menyatu dengan AO map
// - Kontrol tulang bahu dari data MediaPipe Pose

import { useRef, useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import { useClothStore } from './useClothStore'

// ─── Konstanta ────────────────────────────────────────────────────────────────
const MP_LEFT_SHOULDER  = 11
const MP_RIGHT_SHOULDER = 12
const MP_LEFT_ELBOW     = 13
const MP_RIGHT_ELBOW    = 14
const MP_LEFT_HIP       = 23
const MP_RIGHT_HIP      = 24

const BONE_LERP_FACTOR = 0.12

// ─── Helper: hitung sudut bahu dari landmark ──────────────────────────────────
function emaFilter(prev, next, alpha) {
  if (prev === null || prev === undefined) return next
  return prev + alpha * (next - prev)
}

function emaLandmark(prev, next, alpha) {
  if (!prev) return { ...next }
  return {
    x:          emaFilter(prev.x,          next.x,          alpha),
    y:          emaFilter(prev.y,          next.y,          alpha),
    z:          emaFilter(prev.z,          next.z,          alpha),
    visibility: emaFilter(prev.visibility, next.visibility, alpha),
  }
}

// ─── Helper: hitung sudut bahu dari landmark ──────────────────────────────────
function computeShoulderRotation(shoulder, elbow, isLeft) {
  const dx = elbow.x - shoulder.x
  const dy = elbow.y - shoulder.y
  const dz = (elbow.z || 0) - (shoulder.z || 0)

  const abduction = isLeft
    ? Math.atan2(-dy, -dx) - Math.PI / 2
    : Math.atan2(-dy,  dx) - Math.PI / 2

  const flexion = Math.atan2(dz, Math.sqrt(dx * dx + dy * dy)) * 1.2

  return new THREE.Euler(flexion, 0, abduction, 'XYZ')
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function applyTextureMix(material, diffuseTex) {
  if (!material || !material.isMeshStandardMaterial) return

  if (diffuseTex) {
    material.map = diffuseTex
    material.aoMapIntensity = 0.85
  } else {
    material.map = null
  }
  material.needsUpdate = true
}

function lerpEuler(current, target, factor) {
  const qCurrent = new THREE.Quaternion().setFromEuler(current)
  const qTarget  = new THREE.Quaternion().setFromEuler(target)
  qCurrent.slerp(qTarget, factor)
  current.setFromQuaternion(qCurrent)
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function ClothModel({
  modelPath = '/models/baju_rigged.glb',
  scale = 1,
  position = [0, -1.2, 0],
}) {
  const { nodes, materials, scene } = useGLTF(modelPath)

  const selectedTexture = useClothStore(s => s.selectedTexture)
  const poseLandmarks   = useClothStore(s => s.poseLandmarks)

  const targetRotL  = useRef(new THREE.Euler())
  const targetRotR  = useRef(new THREE.Euler())
  const currentRotL = useRef(new THREE.Euler())
  const currentRotR = useRef(new THREE.Euler())
  const smoothLM    = useRef({})

  // ─── Load dan cache tekstur produk ────────────────────────────────
  const diffuseTexture = useMemo(() => {
    if (!selectedTexture) return null

    const loader = new THREE.TextureLoader()
    const tex = loader.load(selectedTexture)
    tex.flipY = false
    tex.colorSpace = THREE.SRGBColorSpace
    tex.wrapS = THREE.RepeatWrapping
    tex.wrapT = THREE.RepeatWrapping
    tex.repeat.set(1, 1)

    return tex
  }, [selectedTexture])

  // ─── Update material saat tekstur berubah ─────────────────────────
  useEffect(() => {
    scene.traverse((child) => {
      if (!child.isMesh && !child.isSkinnedMesh) return
      const mat = child.material
      if (Array.isArray(mat)) {
        mat.forEach(m => applyTextureMix(m, diffuseTexture))
      } else if (mat) {
        applyTextureMix(mat, diffuseTexture)
      }
    })
  }, [diffuseTexture, scene])

  // ─── useFrame: rotasi tulang dari MediaPipe ────────────────────────
  useFrame(() => {
    // Cek nama tulang yang tersedia di GLB ini: Shoulder_L dan Shoulder_R
    const boneL = nodes?.Shoulder_L
    const boneR = nodes?.Shoulder_R

    if (!boneL || !boneR) return

    if (poseLandmarks && poseLandmarks.length >= 15) {
      const lShoulder = poseLandmarks[MP_LEFT_SHOULDER]
      const rShoulder = poseLandmarks[MP_RIGHT_SHOULDER]
      const lElbow    = poseLandmarks[MP_LEFT_ELBOW]
      const rElbow    = poseLandmarks[MP_RIGHT_ELBOW]

      const visThreshold = 0.5
      if (
        lShoulder?.visibility > visThreshold &&
        lElbow?.visibility    > visThreshold &&
        rShoulder?.visibility > visThreshold &&
        rElbow?.visibility    > visThreshold
      ) {
        const sm = smoothLM.current
        const EMA_ALPHA = 0.25
        sm.lSh = emaLandmark(sm.lSh, lShoulder, EMA_ALPHA)
        sm.rSh = emaLandmark(sm.rSh, rShoulder, EMA_ALPHA)
        sm.lEl = emaLandmark(sm.lEl, lElbow,    EMA_ALPHA)
        sm.rEl = emaLandmark(sm.rEl, rElbow,    EMA_ALPHA)

        targetRotL.current = computeShoulderRotation(sm.lSh, sm.lEl, true)
        targetRotR.current = computeShoulderRotation(sm.rSh, sm.rEl, false)
      }
    }

    lerpEuler(currentRotL.current, targetRotL.current, BONE_LERP_FACTOR)
    lerpEuler(currentRotR.current, targetRotR.current, BONE_LERP_FACTOR)

    boneL.rotation.copy(currentRotL.current)
    boneR.rotation.copy(currentRotR.current)
  })

  return (
    <primitive
      object={scene}
      scale={scale}
      position={position}
      dispose={null}
    />
  )
}

useGLTF.preload('/models/baju_rigged.glb')
