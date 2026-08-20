import * as THREE from 'three';
import { cone } from '../game/config.js';

export function createPhysicsWorld(RAPIER) {
  const world = new RAPIER.World({ x: 0, y: -9.8, z: 0 });

  world.createCollider(
    RAPIER.ColliderDesc
      .cylinder(0.18, cone.bottomRadius + 0.35)
      .setTranslation(0, cone.bottomY - 0.18, 0)
      .setFriction(1.0)
  );

  world.createCollider(
    RAPIER.ColliderDesc
      .cylinder(0.22, cone.topRadius + 0.25)
      .setTranslation(0, cone.topY + cone.capPadding, 0)
      .setFriction(0.9)
  );

  const vertices = [];
  const indices = [];
  const segments = 80;

  for (let index = 0; index < segments; index += 1) {
    const angle = (index / segments) * Math.PI * 2;
    vertices.push(
      Math.cos(angle) * cone.topRadius, cone.topY, Math.sin(angle) * cone.topRadius,
      Math.cos(angle) * cone.bottomRadius, cone.bottomY, Math.sin(angle) * cone.bottomRadius
    );
  }

  for (let index = 0; index < segments; index += 1) {
    const next = (index + 1) % segments;
    const topA = index * 2;
    const bottomA = index * 2 + 1;
    const topB = next * 2;
    const bottomB = next * 2 + 1;
    indices.push(topA, topB, bottomA, topB, bottomB, bottomA);
  }

  world.createCollider(
    RAPIER.ColliderDesc
      .trimesh(new Float32Array(vertices), new Uint32Array(indices))
      .setFriction(0.95)
      .setRestitution(0.05)
  );

  return world;
}

export function keepItemInsideCone(item, radiusAtY) {
  const pos = item.body.translation();
  const vel = item.body.linvel();
  let x = pos.x;
  let y = THREE.MathUtils.clamp(pos.y, cone.bottomY + cone.itemRadius, cone.topY + cone.capPadding - cone.itemRadius);
  let z = pos.z;
  let vx = vel.x;
  let vy = vel.y;
  let vz = vel.z;
  const maxRadius = Math.max(radiusAtY(y) - cone.itemRadius, 0.1);
  const radial = Math.hypot(x, z);

  if (radial > maxRadius) {
    const nx = x / radial;
    const nz = z / radial;
    x = nx * maxRadius;
    z = nz * maxRadius;
    const outwardVelocity = vx * nx + vz * nz;
    if (outwardVelocity > 0) {
      vx -= outwardVelocity * nx * 1.45;
      vz -= outwardVelocity * nz * 1.45;
    }
  }

  if (pos.y !== y) {
    vy = pos.y > y ? Math.min(vy, 0) : Math.max(vy, 0);
  }

  if (x !== pos.x || y !== pos.y || z !== pos.z) {
    item.body.setTranslation({ x, y, z }, true);
    item.body.setLinvel({ x: vx, y: vy, z: vz }, true);
  }
}