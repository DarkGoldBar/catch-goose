import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import {
  colliderPadding,
  cone,
  ellipsoidLatitudeSegments,
  ellipsoidLongitudeSegments,
  modelDisplayScale
} from '../game/config.js';

const gltfLoader = new GLTFLoader();
const modelCache = new Map();

export async function createItemMesh(type) {
  if (!type.modelUrl) {
    throw new Error(`Missing model for ${type.name}.`);
  }

  let template = modelCache.get(type.modelUrl);
  if (!template) {
    const gltf = await gltfLoader.loadAsync(type.modelUrl);
    template = normalizeModelTemplate(gltf.scene);
    modelCache.set(type.modelUrl, template);
  }

  const clone = template.clone(true);
  clone.name = type.name;
  clone.scale.setScalar(0.82 * modelDisplayScale * type.modelScale);
  clone.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = false;
    }
  });
  clone.userData.ellipsoidCollider = buildEllipsoidColliderData(clone);
  return clone;
}

function normalizeModelTemplate(model) {
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
  root.scale.setScalar(0.9 / largest);
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