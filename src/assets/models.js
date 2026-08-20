import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import celebrationGooseUrl from '../../assets/models/goose.glb?url';
import {
  colliderPadding,
  cone,
  ellipsoidLatitudeSegments,
  ellipsoidLongitudeSegments,
  modelMaterialEmissiveIntensity,
  modelMaterialLightness,
  modelScale
} from '../config.js';

const gltfLoader = new GLTFLoader();
const modelCache = new Map();
const materialTextureKeys = [
  'map',
  'emissiveMap',
  'aoMap',
  'normalMap',
  'roughnessMap',
  'metalnessMap',
  'alphaMap',
  'bumpMap',
  'displacementMap',
  'lightMap'
];

export async function createItemMesh(type) {
  if (!type.modelUrl) {
    throw new Error(`Missing model for ${type.name}.`);
  }

  const templateCacheKey = `${type.modelUrl}:${type.modelScale}`;
  let template = modelCache.get(templateCacheKey);
  if (!template) {
    const gltf = await gltfLoader.loadAsync(type.modelUrl);
    template = normalizeModelTemplate(gltf.scene, type.modelScale);
    brightenModelMaterials(template);
    modelCache.set(templateCacheKey, template);
  }

  const clone = template.clone(true);
  clone.name = type.name;
  clone.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = false;
    }
  });
  clone.userData.ellipsoidCollider = buildEllipsoidColliderData(clone);
  return clone;
}

export async function createCelebrationGooseMesh() {
  const templateCacheKey = `${celebrationGooseUrl}:celebration`;
  let template = modelCache.get(templateCacheKey);
  if (!template) {
    const gltf = await gltfLoader.loadAsync(celebrationGooseUrl);
    template = normalizeModelTemplate(gltf.scene, 1);
    brightenModelMaterials(template);
    modelCache.set(templateCacheKey, template);
  }

  const clone = template.clone(true);
  clone.name = 'celebration-goose';
  clone.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = false;
    }
  });
  return clone;
}

function brightenModelMaterials(model) {
  const updatedMaterials = new Set();
  model.traverse((child) => {
    if (!child.isMesh) return;
    updateMaterialBrightness(child.material, updatedMaterials);
  });
}

function updateMaterialBrightness(material, updatedMaterials) {
  if (Array.isArray(material)) {
    material.forEach((entry) => updateMaterialBrightness(entry, updatedMaterials));
    return;
  }
  if (!material || material.isMeshBasicMaterial) return;
  if (!hasMaterialTexture(material)) return;
  if (updatedMaterials.has(material)) return;
  updatedMaterials.add(material);

  if (material.color) {
    material.color.multiplyScalar(modelMaterialLightness);
  }
  if (material.emissive && material.color) {
    material.emissive.copy(material.color);
    material.emissiveIntensity = modelMaterialEmissiveIntensity;
  }
  if (material.map && 'emissiveMap' in material) {
    material.emissiveMap = material.map;
  }
  material.needsUpdate = true;
}

function hasMaterialTexture(material) {
  return materialTextureKeys.some((key) => material[key]?.isTexture);
}

function normalizeModelTemplate(model, itemModelScale) {
  model.updateMatrixWorld(true);
  const box = getVertexBoundsInRootSpace(model);
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  const largest = Math.max(size.x, size.y, size.z) || 1;

  const root = new THREE.Group();
  root.name = model.name || 'centered-model';
  model.position.sub(center);
  root.add(model);
  root.scale.setScalar((modelScale * itemModelScale) / largest);
  root.updateMatrixWorld(true);
  return root;
}

function buildEllipsoidColliderData(root) {
  const bounds = getVertexBoundsInRootSpace(root);
  if (bounds.isEmpty()) return null;

  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  bounds.getSize(size);
  bounds.getCenter(center);

  const scale = root.scale;
  const radii = new THREE.Vector3(
    Math.max(size.x * Math.abs(scale.x) * 0.5 + colliderPadding, cone.itemRadius * 0.45),
    Math.max(size.y * Math.abs(scale.y) * 0.5 + colliderPadding, cone.itemRadius * 0.45),
    Math.max(size.z * Math.abs(scale.z) * 0.5 + colliderPadding, cone.itemRadius * 0.45)
  );
  const scaledCenter = center.multiply(scale);
  const points = [];
  points.push(scaledCenter.x, scaledCenter.y + radii.y, scaledCenter.z);
  points.push(scaledCenter.x, scaledCenter.y - radii.y, scaledCenter.z);

  for (let lat = 1; lat < ellipsoidLatitudeSegments; lat += 1) {
    const phi = (lat / ellipsoidLatitudeSegments) * Math.PI;
    const y = Math.cos(phi) * radii.y;
    const ring = Math.sin(phi);

    for (let lon = 0; lon < ellipsoidLongitudeSegments; lon += 1) {
      const theta = (lon / ellipsoidLongitudeSegments) * Math.PI * 2;
      points.push(
        scaledCenter.x + Math.cos(theta) * ring * radii.x,
        scaledCenter.y + y,
        scaledCenter.z + Math.sin(theta) * ring * radii.z
      );
    }
  }

  return { points: new Float32Array(points) };
}

function getVertexBoundsInRootSpace(model) {
  const box = new THREE.Box3();
  const vertex = new THREE.Vector3();
  const rootInverse = model.matrixWorld.clone().invert();
  let hasVertices = false;

  model.traverse((child) => {
    if (!child.isMesh || !child.geometry?.attributes?.position) return;
    const positions = child.geometry.attributes.position;

    for (let index = 0; index < positions.count; index += 1) {
      vertex
        .fromBufferAttribute(positions, index)
        .applyMatrix4(child.matrixWorld)
        .applyMatrix4(rootInverse);
      box.expandByPoint(vertex);
      hasVertices = true;
    }
  });

  return hasVertices ? box : new THREE.Box3().setFromObject(model);
}
