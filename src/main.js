import * as THREE from 'three';
import RAPIER from '@dimforge/rapier3d-compat';
import './style.css';

const app = document.querySelector('#app');
app.innerHTML = `
  <main class="game-shell">
    <section class="topbar">
      <h1>抓大鹅</h1>
    </section>
    <section class="stage-wrap">
      <canvas id="gameCanvas" aria-label="抓大鹅游戏画面"></canvas>
      <div class="left-badge">剩余 <strong id="leftCount">0</strong></div>
      <div id="message" class="message hidden"></div>
    </section>
    <section class="controls">
      <button id="shuffleBtn" type="button">晃一下</button>
      <button id="restartBtn" type="button">重新开始</button>
    </section>
  </main>
`;

const canvas = document.querySelector('#gameCanvas');
const leftCountEl = document.querySelector('#leftCount');
const messageEl = document.querySelector('#message');

const traySize = 8;
const cone = {
  topY: 4.4,
  bottomY: -4.2,
  topRadius: 4.15,
  bottomRadius: 0.95,
  capPadding: 0.5,
  itemRadius: 0.38
};

const trayConfig = {
  y: 0.35,
  z: 4.35,
  spacing: 0.82,
  slotSize: 0.68
};

const itemTypes = [
  { name: '鹅', color: 0xf8f2df, accent: 0xf0b33e, shape: 'goose' },
  { name: '苹果', color: 0xd9463e, accent: 0x7a3322, shape: 'sphere' },
  { name: '梨', color: 0xd7dc66, accent: 0x5a8c48, shape: 'pear' },
  { name: '包子', color: 0xf0e1c6, accent: 0xc9a06a, shape: 'bun' },
  { name: '碗', color: 0x6aa5d8, accent: 0xffffff, shape: 'bowl' },
  { name: '木鱼', color: 0xb96f3c, accent: 0x60351f, shape: 'capsule' },
  { name: '萝卜', color: 0xfff4ea, accent: 0x58a75b, shape: 'carrot' },
  { name: '金蛋', color: 0xf2c94c, accent: 0xfff0a8, shape: 'egg' }
];

let renderer;
let scene;
let camera;
let world;
let bodies = [];
let tray = [];
let traySlots = [];
let removed = 0;
let gameOver = false;
let pointer = new THREE.Vector2();
let raycaster = new THREE.Raycaster();
let lastTime = performance.now();
let hoveredItem = null;
let pressedItem = null;

start();

async function start() {
  await RAPIER.init();
  init();
  restart();
  requestAnimationFrame(tick);
}

function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe9efe7);

  camera = new THREE.OrthographicCamera(-5.4, 5.4, 5.4, -5.4, 0.1, 30);
  camera.position.set(0, 12, 0);
  camera.up.set(0, 0, -1);
  camera.lookAt(0, 0, 0);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x727b6c, 2.7));

  const sun = new THREE.DirectionalLight(0xffffff, 2.3);
  sun.position.set(0, 9, 0.6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -6;
  sun.shadow.camera.right = 6;
  sun.shadow.camera.top = 6;
  sun.shadow.camera.bottom = -6;
  scene.add(sun);

  createInvisibleShadowReceiver();
  createTraySlots();

  window.addEventListener('resize', resize);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('pointerleave', onPointerLeave);
  document.querySelector('#restartBtn').addEventListener('click', restart);
  document.querySelector('#shuffleBtn').addEventListener('click', shakeCone);
  resize();
}

function createInvisibleShadowReceiver() {
  const shadowMat = new THREE.ShadowMaterial({ color: 0x253c2b, opacity: 0.18 });
  const receiver = new THREE.Mesh(new THREE.CircleGeometry(cone.topRadius, 72), shadowMat);
  receiver.rotation.x = -Math.PI / 2;
  receiver.position.y = cone.bottomY - 0.03;
  receiver.receiveShadow = true;
  scene.add(receiver);
}

function createTraySlots() {
  const slotMaterial = new THREE.MeshStandardMaterial({
    color: 0xfffbef,
    roughness: 0.78,
    metalness: 0.02
  });
  const edgeMaterial = new THREE.MeshStandardMaterial({
    color: 0x90a487,
    roughness: 0.7
  });

  for (let i = 0; i < traySize; i += 1) {
    const group = new THREE.Group();
    const base = new THREE.Mesh(new THREE.BoxGeometry(trayConfig.slotSize, 0.08, trayConfig.slotSize), slotMaterial);
    const thickness = 0.035;
    const span = trayConfig.slotSize + thickness;
    const top = new THREE.Mesh(new THREE.BoxGeometry(span, 0.045, thickness), edgeMaterial);
    const bottom = top.clone();
    const left = new THREE.Mesh(new THREE.BoxGeometry(thickness, 0.045, span), edgeMaterial);
    const right = left.clone();
    top.position.set(0, 0.07, -trayConfig.slotSize / 2);
    bottom.position.set(0, 0.07, trayConfig.slotSize / 2);
    left.position.set(-trayConfig.slotSize / 2, 0.07, 0);
    right.position.set(trayConfig.slotSize / 2, 0.07, 0);
    group.add(base, top, bottom, left, right);
    group.position.copy(getTraySlotPosition(i));
    group.userData.slotIndex = i;
    group.traverse((child) => {
      if (child.isMesh) child.receiveShadow = true;
    });
    traySlots.push(group);
    scene.add(group);
  }
}

function createPhysics() {
  world = new RAPIER.World({ x: 0, y: -9.8, z: 0 });

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

  for (let i = 0; i < segments; i += 1) {
    const angle = (i / segments) * Math.PI * 2;
    vertices.push(
      Math.cos(angle) * cone.topRadius, cone.topY, Math.sin(angle) * cone.topRadius,
      Math.cos(angle) * cone.bottomRadius, cone.bottomY, Math.sin(angle) * cone.bottomRadius
    );
  }

  for (let i = 0; i < segments; i += 1) {
    const next = (i + 1) % segments;
    const topA = i * 2;
    const bottomA = i * 2 + 1;
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
}

function restart() {
  setHighlightedItem(null);
  pressedItem = null;
  bodies.forEach(({ mesh }) => scene.remove(mesh));
  bodies = [];
  tray = [];
  removed = 0;
  gameOver = false;
  hideMessage();
  createPhysics();

  const deck = [];
  itemTypes.forEach((type, typeIndex) => {
    for (let i = 0; i < 6; i += 1) deck.push(typeIndex);
  });
  deck.sort(() => Math.random() - 0.5);

  deck.forEach((typeIndex, index) => {
    const y = 2.6 + index * 0.035;
    const point = randomPointInCircle(radiusAtY(y) - 0.75);
    createItem(typeIndex, point.x, y, point.z);
  });

  layoutTray();
  updateHud();
}

function createItem(typeIndex, x, y, z) {
  const type = itemTypes[typeIndex];
  const mesh = makeMesh(type);
  mesh.position.set(x, y, z);
  mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
  mesh.userData.typeIndex = typeIndex;
  mesh.userData.name = type.name;
  scene.add(mesh);

  const body = world.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(x, y, z)
      .setRotation({ x: mesh.quaternion.x, y: mesh.quaternion.y, z: mesh.quaternion.z, w: mesh.quaternion.w })
      .setLinearDamping(0.42)
      .setAngularDamping(0.45)
  );
  world.createCollider(
    RAPIER.ColliderDesc
      .ball(cone.itemRadius)
      .setRestitution(0.08)
      .setFriction(0.95),
    body
  );

  bodies.push({
    mesh,
    body,
    typeIndex,
    status: 'active',
    baseScale: mesh.scale.x,
    animation: null
  });
}

function makeMesh(type) {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: type.color, roughness: 0.58, metalness: 0.03 });
  const accent = new THREE.MeshStandardMaterial({ color: type.accent, roughness: 0.7 });

  if (type.shape === 'goose') {
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.35, 24, 16), mat);
    body.scale.set(1.15, 0.78, 0.9);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.17, 18, 12), mat);
    head.position.set(0.32, 0.25, -0.08);
    const beak = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.18, 16), accent);
    beak.position.set(0.48, 0.24, -0.08);
    beak.rotation.z = -Math.PI / 2;
    group.add(body, head, beak);
  } else if (type.shape === 'pear') {
    const bottom = new THREE.Mesh(new THREE.SphereGeometry(0.32, 24, 16), mat);
    const top = new THREE.Mesh(new THREE.SphereGeometry(0.22, 24, 16), mat);
    top.position.y = 0.25;
    const leaf = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.18, 12), accent);
    leaf.position.set(0.05, 0.48, 0);
    group.add(bottom, top, leaf);
  } else if (type.shape === 'bun') {
    const bun = new THREE.Mesh(new THREE.SphereGeometry(0.38, 24, 16), mat);
    bun.scale.set(1, 0.55, 1);
    const fold = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.02, 8, 24), accent);
    fold.rotation.x = Math.PI / 2;
    fold.position.y = 0.22;
    group.add(bun, fold);
  } else if (type.shape === 'bowl') {
    const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.28, 0.28, 28), mat);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.035, 8, 32), accent);
    rim.position.y = 0.15;
    rim.rotation.x = Math.PI / 2;
    group.add(bowl, rim);
  } else if (type.shape === 'capsule') {
    const capsule = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 0.38, 8, 18), mat);
    capsule.rotation.z = Math.PI / 2;
    const stripe = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.018, 8, 24), accent);
    stripe.rotation.y = Math.PI / 2;
    group.add(capsule, stripe);
  } else if (type.shape === 'carrot') {
    const root = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.65, 20), mat);
    root.rotation.z = Math.PI;
    const leaf = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.28, 12), accent);
    leaf.position.y = 0.42;
    group.add(root, leaf);
  } else if (type.shape === 'egg') {
    const egg = new THREE.Mesh(new THREE.SphereGeometry(0.34, 24, 16), mat);
    egg.scale.set(0.8, 1.1, 0.8);
    const shine = new THREE.Mesh(new THREE.SphereGeometry(0.08, 12, 8), new THREE.MeshStandardMaterial({ color: type.accent, roughness: 0.2 }));
    shine.position.set(0.12, 0.18, 0.18);
    group.add(egg, shine);
  } else {
    group.add(new THREE.Mesh(new THREE.SphereGeometry(0.35, 24, 16), mat));
  }

  group.scale.setScalar(0.92);
  group.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  return group;
}

function onPointerMove(event) {
  if (gameOver) return;
  setHighlightedItem(getPointerItem(event));
}

function onPointerDown(event) {
  if (gameOver) return;
  canvas.setPointerCapture?.(event.pointerId);
  pressedItem = getPointerItem(event);
  setHighlightedItem(pressedItem);
}

function onPointerUp(event) {
  if (gameOver) return;
  canvas.releasePointerCapture?.(event.pointerId);
  const releasedItem = getPointerItem(event);
  const selectedItem = releasedItem || pressedItem;
  pressedItem = null;

  if (selectedItem && selectedItem === hoveredItem) {
    setHighlightedItem(null);
    selectItem(selectedItem);
  } else {
    setHighlightedItem(releasedItem);
  }
}

function onPointerLeave() {
  if (!pressedItem) setHighlightedItem(null);
}

function getPointerItem(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const activeMeshes = bodies.filter((item) => item.status === 'active').map((item) => item.mesh);
  const hits = raycaster.intersectObjects(activeMeshes, true);
  if (!hits.length) return null;

  let target = hits[0].object;
  while (target.parent && !target.userData.name) target = target.parent;
  return bodies.find((entry) => entry.mesh === target && entry.status === 'active') || null;
}

function setHighlightedItem(item) {
  if (hoveredItem === item) return;
  if (hoveredItem) removeItemHighlight(hoveredItem);
  hoveredItem = item;
  if (hoveredItem) addItemHighlight(hoveredItem);
}

function addItemHighlight(item) {
  removeItemHighlight(item);

  const overlayMaterial = new THREE.MeshBasicMaterial({
    color: 0xffdc3a,
    transparent: true,
    opacity: 0.34,
    depthWrite: false
  });
  const outlineMaterial = new THREE.MeshBasicMaterial({
    color: 0xffc400,
    side: THREE.BackSide,
    transparent: true,
    opacity: 0.95,
    depthWrite: false
  });
  const overlay = new THREE.Group();
  const outline = new THREE.Group();

  item.mesh.children.forEach((child) => {
    if (!child.isMesh) return;
    const overlayMesh = new THREE.Mesh(child.geometry, overlayMaterial);
    overlayMesh.position.copy(child.position);
    overlayMesh.quaternion.copy(child.quaternion);
    overlayMesh.scale.copy(child.scale);
    overlay.add(overlayMesh);

    const outlineMesh = new THREE.Mesh(child.geometry, outlineMaterial);
    outlineMesh.position.copy(child.position);
    outlineMesh.quaternion.copy(child.quaternion);
    outlineMesh.scale.copy(child.scale);
    outline.add(outlineMesh);
  });

  outline.scale.setScalar(1.18);
  overlay.scale.setScalar(1.035);
  overlay.renderOrder = 10;
  outline.renderOrder = 9;
  item.mesh.add(outline, overlay);
  item.highlight = { overlay, outline, overlayMaterial, outlineMaterial };
}

function removeItemHighlight(item) {
  if (!item.highlight) return;
  item.mesh.remove(item.highlight.overlay, item.highlight.outline);
  item.highlight.overlayMaterial.dispose();
  item.highlight.outlineMaterial.dispose();
  item.highlight = null;
}

function selectItem(item) {
  if (tray.filter((entry) => entry.status !== 'gone').length >= traySize) return;
  removeItemHighlight(item);
  if (hoveredItem === item) hoveredItem = null;

  item.status = 'movingToTray';
  world.removeRigidBody(item.body);
  item.body = null;
  tray.push(item);
  removed += 1;
  moveItemToTray(item, tray.length - 1);
  updateHud();
}

function moveItemToTray(item, slotIndex) {
  const target = getTraySlotPosition(slotIndex);
  item.animation = {
    kind: 'moveToTray',
    from: item.mesh.position.clone(),
    to: new THREE.Vector3(target.x, target.y + 0.42, target.z),
    startScale: item.mesh.scale.x,
    endScale: item.baseScale * 0.82,
    start: performance.now(),
    duration: 360
  };
}

function layoutTray() {
  tray.forEach((item, index) => {
    if (item.status === 'tray') {
      const target = getTraySlotPosition(index);
      item.animation = {
        kind: 'moveToSlot',
        from: item.mesh.position.clone(),
        to: new THREE.Vector3(target.x, target.y + 0.42, target.z),
        startScale: item.mesh.scale.x,
        endScale: item.baseScale * 0.82,
        start: performance.now(),
        duration: 220
      };
    }
  });
}

function checkMatches() {
  const counts = new Map();
  tray
    .filter((item) => item.status === 'tray')
    .forEach((item) => counts.set(item.typeIndex, (counts.get(item.typeIndex) || 0) + 1));

  for (const [typeIndex, count] of counts) {
    if (count >= 3) {
      const matched = tray.filter((item) => item.status === 'tray' && item.typeIndex === typeIndex).slice(0, 3);
      matched.forEach((item) => {
        item.status = 'matching';
        item.animation = {
          kind: 'match',
          start: performance.now(),
          duration: 520,
          baseScale: item.mesh.scale.x
        };
      });
      break;
    }
  }
}

function finishMatch(item) {
  item.status = 'gone';
  item.animation = null;
  scene.remove(item.mesh);
  tray = tray.filter((entry) => entry.status !== 'gone');
  layoutTray();
  checkEndState();
}

function checkEndState() {
  const visibleTrayCount = tray.filter((entry) => entry.status !== 'gone').length;
  const animatingMatches = tray.some((entry) => entry.status === 'matching');

  if (removed === bodies.length && visibleTrayCount === 0 && !animatingMatches) {
    gameOver = true;
    showMessage('通关了');
  } else if (visibleTrayCount >= traySize && !animatingMatches) {
    gameOver = true;
    showMessage('暂存栏满了');
  }
}

function shakeCone() {
  if (gameOver) return;
  bodies.forEach((item) => {
    if (item.status !== 'active') return;
    const pos = item.body.translation();
    const radial = new THREE.Vector2(pos.x, pos.z);
    const inward = radial.lengthSq() > 0.001 ? radial.normalize().multiplyScalar(-1) : randomDirection2();
    const swirl = new THREE.Vector2(-inward.y, inward.x).multiplyScalar((Math.random() - 0.5) * 3.8);
    item.body.applyImpulse({
      x: inward.x * (0.9 + Math.random() * 1.4) + swirl.x,
      y: 1.4 + Math.random() * 1.6,
      z: inward.y * (0.9 + Math.random() * 1.4) + swirl.y
    }, true);
    item.body.applyTorqueImpulse({
      x: (Math.random() - 0.5) * 2.8,
      y: (Math.random() - 0.5) * 2.8,
      z: (Math.random() - 0.5) * 2.8
    }, true);
  });
}

function updateHud() {
  leftCountEl.textContent = String(bodies.length - removed);
}

function updateAnimation(item, now) {
  if (!item.animation) return;
  const progress = THREE.MathUtils.clamp((now - item.animation.start) / item.animation.duration, 0, 1);
  const eased = easeOutCubic(progress);

  if (item.animation.kind === 'moveToTray' || item.animation.kind === 'moveToSlot') {
    item.mesh.position.lerpVectors(item.animation.from, item.animation.to, eased);
    item.mesh.scale.setScalar(THREE.MathUtils.lerp(item.animation.startScale, item.animation.endScale, eased));
    item.mesh.rotation.y += 0.08;
    if (progress >= 1) {
      item.status = 'tray';
      item.animation = null;
      checkMatches();
      checkEndState();
    }
  } else if (item.animation.kind === 'match') {
    const scalePhase = progress < 0.35
      ? THREE.MathUtils.lerp(item.animation.baseScale, item.baseScale * 1.2, progress / 0.35)
      : THREE.MathUtils.lerp(item.baseScale * 1.2, 0.01, (progress - 0.35) / 0.65);
    item.mesh.scale.setScalar(scalePhase);
    item.mesh.rotation.y += 0.12;
    if (progress >= 1) finishMatch(item);
  }
}

function radiusAtY(y) {
  const t = THREE.MathUtils.clamp((y - cone.bottomY) / (cone.topY - cone.bottomY), 0, 1);
  return THREE.MathUtils.lerp(cone.bottomRadius, cone.topRadius, t);
}

function randomPointInCircle(radius) {
  const angle = Math.random() * Math.PI * 2;
  const distance = Math.sqrt(Math.random()) * radius;
  return {
    x: Math.cos(angle) * distance,
    z: Math.sin(angle) * distance
  };
}

function randomDirection2() {
  const angle = Math.random() * Math.PI * 2;
  return new THREE.Vector2(Math.cos(angle), Math.sin(angle));
}

function getTraySlotPosition(index) {
  const visibleWidth = camera ? camera.right - camera.left : 10.8;
  const responsiveSpacing = Math.min(
    trayConfig.spacing,
    Math.max(0.5, (visibleWidth - trayConfig.slotSize - 0.45) / (traySize - 1))
  );

  return new THREE.Vector3(
    (index - (traySize - 1) / 2) * responsiveSpacing,
    trayConfig.y,
    trayConfig.z
  );
}

function keepInsideCone(item) {
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

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.classList.remove('hidden');
}

function hideMessage() {
  messageEl.textContent = '';
  messageEl.classList.add('hidden');
}

function easeOutCubic(value) {
  return 1 - Math.pow(1 - value, 3);
}

function tick(now) {
  const delta = Math.min((now - lastTime) / 1000, 0.033);
  lastTime = now;
  if (world) world.timestep = delta;
  if (world && !gameOver) world.step();

  bodies.forEach((item) => {
    if (item.status === 'gone') return;
    if (item.status === 'active') {
      keepInsideCone(item);
      const pos = item.body.translation();
      const rot = item.body.rotation();
      item.mesh.position.set(pos.x, pos.y, pos.z);
      item.mesh.quaternion.set(rot.x, rot.y, rot.z, rot.w);
    } else {
      updateAnimation(item, now);
    }
  });

  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

function resize() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(rect.width, 1);
  const height = Math.max(rect.height, 1);
  renderer.setSize(width, height, false);

  const view = 10.7;
  const aspect = width / height;
  camera.left = -view * aspect * 0.5;
  camera.right = view * aspect * 0.5;
  camera.top = view * 0.5;
  camera.bottom = -view * 0.5;
  camera.updateProjectionMatrix();

  traySlots.forEach((slot, index) => {
    slot.position.copy(getTraySlotPosition(index));
  });
  layoutTray();
}
