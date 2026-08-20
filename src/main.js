import * as THREE from 'three';
import bgmUrl from '../assets/bgm.mp3?url';
import {
  getDefaultTheme,
  getRandomTheme,
  getThemeBackgroundUrl,
  getThemeItemTypes
} from './assets/catalog.js';
import { createItemMesh } from './assets/models.js';
import { createPhysicsWorld, keepItemInsideCone } from './physics/world.js';
import { createGameDom } from './ui/dom.js';
import {
  cone,
  fixedTimeStep,
  initialItemCount,
  maxFrameDelta,
  maxPhysicsStepsPerFrame,
  trayConfig,
  trayEulerArgs,
  traySize
} from './game/config.js';
import { easeOutCubic, randomPointInCircle } from './utils/math.js';
import './style.css';

const trayEuler = new THREE.Euler(...trayEulerArgs);
const trayQuaternion = new THREE.Quaternion().setFromEuler(trayEuler);

const app = document.querySelector('#app');
const {
  canvas,
  leftCount: leftCountEl,
  message: messageEl,
  restartButton,
  shuffleButton,
  timeCount: timeCountEl
} = createGameDom(app);

let itemTypes = [];

let RAPIER;
let renderer;
let scene;
let camera;
let world;
let bodies = [];
let tray = [];
let traySlots = [];
let traySlotItems = createEmptyTraySlots();
let removed = 0;
let gameOver = false;
let pointer = new THREE.Vector2();
let raycaster = new THREE.Raycaster();
let lastTime = performance.now();
let physicsAccumulator = 0;
let animationFrameId = null;
let hoveredItem = null;
let pressedItem = null;
let bgm;
let selectedTheme = null;
let gameStartTime = performance.now();
let trayLayout = {
  spacing: trayConfig.spacing,
  slotScale: 1,
  itemScale: 1
};

start();

async function start() {
  // loaded lazily so the large wasm bundle becomes its own chunk
  RAPIER = (await import('@dimforge/rapier3d')).default;
  await RAPIER.init();
  init();
  await restart();
  startRenderLoop();
}

function startRenderLoop() {
  if (animationFrameId != null) cancelAnimationFrame(animationFrameId);
  lastTime = performance.now();
  physicsAccumulator = 0;
  animationFrameId = requestAnimationFrame(tick);
}

function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;

  scene = new THREE.Scene();
  scene.background = null;1

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
  setupBgm();

  window.addEventListener('resize', resize);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('pointerleave', onPointerLeave);
  restartButton.addEventListener('click', restart);
  shuffleButton.addEventListener('click', shakeCone);
  resize();
}

function setupBgm() {
  bgm = new Audio(bgmUrl);
  bgm.loop = true;
  bgm.preload = 'auto';
  bgm.volume = 0.42;

  const play = () => {
    bgm.play().catch(() => {
      window.addEventListener('pointerdown', play, { once: true });
      window.addEventListener('keydown', play, { once: true });
    });
  };

  play();
}

function updateStageBackground() {
  const backgroundUrl = getThemeBackgroundUrl(getSelectedTheme());
  canvas.parentElement.style.setProperty('--stage-background-image', backgroundUrl ? `url("${backgroundUrl}")` : 'none');
}

function getSelectedTheme() {
  return selectedTheme || getDefaultTheme();
}

function pickRandomTheme() {
  selectedTheme = getRandomTheme();
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

async function restart() {
  setHighlightedItem(null);
  pressedItem = null;
  pickRandomTheme();
  updateStageBackground();
  bodies.forEach(({ mesh }) => scene.remove(mesh));
  bodies = [];
  tray = [];
  traySlotItems = createEmptyTraySlots();
  removed = 0;
  gameOver = false;
  gameStartTime = performance.now();
  updateTimer(gameStartTime);
  hideMessage();
  itemTypes = getSelectedItemTypes();
  world = createPhysicsWorld(RAPIER);

  const deck = createMatchableDeck(itemTypes.length, initialItemCount);
  deck.sort(() => Math.random() - 0.5);

  for (const [index, typeIndex] of deck.entries()) {
    const y = 2.6 + index * 0.035;
    const point = randomPointInCircle(radiusAtY(y) - 0.75);
    await createItem(typeIndex, point.x, y, point.z);
  }

  layoutTray();
  updateHud();
}

function getSelectedItemTypes() {
  return getThemeItemTypes(getSelectedTheme());
}

function createMatchableDeck(typeCount, itemCount) {
  const copiesByType = Array.from({ length: typeCount }, () => 0);
  const tripleCount = Math.floor(itemCount / 3);

  for (let i = 0; i < tripleCount; i += 1) {
    copiesByType[i % typeCount] += 3;
  }

  return copiesByType.flatMap((copies, typeIndex) => (
    Array.from({ length: copies }, () => typeIndex)
  ));
}

async function createItem(typeIndex, x, y, z) {
  const type = itemTypes[typeIndex];
  const mesh = await createItemMesh(type);
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
  world.createCollider(createItemColliderDesc(mesh), body);

  const item = {
    mesh,
    body,
    typeIndex,
    status: 'active',
    baseScale: mesh.scale.x,
    animation: null
  };
  bindItemInteraction(item);
  bodies.push(item);
}

function createItemColliderDesc(mesh) {
  const ellipsoid = mesh.userData.ellipsoidCollider;
  const desc = ellipsoid
    ? RAPIER.ColliderDesc.convexHull(ellipsoid.points) ?? RAPIER.ColliderDesc.ball(cone.itemRadius)
    : RAPIER.ColliderDesc.ball(cone.itemRadius);

  return desc
    .setRestitution(0.08)
    .setFriction(0.95);
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

  const activeItems = bodies.filter((item) => item.status === 'active');
  const hits = raycaster.intersectObjects(activeItems.map((item) => item.mesh), true);

  for (const hit of hits) {
    const item = getItemFromObject(hit.object);
    if (item) return item;
  }
  return null;
}

function bindItemInteraction(item) {
  item.mesh.userData.item = item;
  item.mesh.traverse((child) => {
    child.userData.item = item;
  });
}

function getItemFromObject(object) {
  let target = object;
  while (target) {
    const item = target.userData?.item;
    if (item?.status === 'active') return item;
    target = target.parent;
  }
  return null;
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

  item.mesh.updateMatrixWorld(true);
  const inverseRoot = item.mesh.matrixWorld.clone().invert();
  item.mesh.traverse((child) => {
    if (!child.isMesh) return;
    const overlayMesh = new THREE.Mesh(child.geometry, overlayMaterial);
    overlayMesh.matrixAutoUpdate = false;
    overlayMesh.matrix.copy(inverseRoot).multiply(child.matrixWorld);
    overlay.add(overlayMesh);

    const outlineMesh = new THREE.Mesh(child.geometry, outlineMaterial);
    outlineMesh.matrixAutoUpdate = false;
    outlineMesh.matrix.copy(inverseRoot).multiply(child.matrixWorld);
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
  if (item.status !== 'active') return;
  const slotIndex = findFirstOpenTraySlot();
  if (slotIndex === -1) return;
  removeItemHighlight(item);
  if (hoveredItem === item) hoveredItem = null;

  item.status = 'movingToTray';
  world.removeRigidBody(item.body);
  item.body = null;
  item.traySlotIndex = slotIndex;
  traySlotItems[slotIndex] = item;
  tray.push(item);
  removed += 1;
  moveItemToTray(item, slotIndex);
  updateHud();
}

function moveItemToTray(item, slotIndex) {
  const target = getTraySlotPosition(slotIndex);
  item.animation = {
    kind: 'moveToTray',
    from: item.mesh.position.clone(),
    to: new THREE.Vector3(target.x, target.y + 0.42, target.z),
    fromQuaternion: item.mesh.quaternion.clone(),
    toQuaternion: trayQuaternion.clone(),
    startScale: item.mesh.scale.x,
    endScale: getTrayItemScale(item),
    start: performance.now(),
    duration: 360
  };
}

function layoutTray() {
  traySlotItems.forEach((item, slotIndex) => {
    if (item && (item.status === 'tray' || item.status === 'movingToTray')) {
      moveItemToSlot(item, slotIndex, 220);
    }
  });
}

function createEmptyTraySlots() {
  return Array.from({ length: traySize }, () => null);
}

function findFirstOpenTraySlot() {
  return traySlotItems.findIndex((item) => item === null);
}

function moveItemToSlot(item, slotIndex, duration) {
  const target = getTraySlotPosition(slotIndex);
  item.traySlotIndex = slotIndex;
  item.animation = {
    kind: 'moveToSlot',
    from: item.mesh.position.clone(),
    to: new THREE.Vector3(target.x, target.y + 0.42, target.z),
    fromQuaternion: item.mesh.quaternion.clone(),
    toQuaternion: trayQuaternion.clone(),
    startScale: item.mesh.scale.x,
    endScale: getTrayItemScale(item),
    start: performance.now(),
    duration
  };
}

function compactTraySlots() {
  const remaining = traySlotItems.filter((item) => item && item.status !== 'gone');
  traySlotItems = createEmptyTraySlots();

  remaining.forEach((item, slotIndex) => {
    traySlotItems[slotIndex] = item;
    if (item.traySlotIndex !== slotIndex || item.status === 'movingToTray') {
      moveItemToSlot(item, slotIndex, 220);
    } else {
      item.traySlotIndex = slotIndex;
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
  if (item.traySlotIndex != null && traySlotItems[item.traySlotIndex] === item) {
    traySlotItems[item.traySlotIndex] = null;
  }
  tray = tray.filter((entry) => entry.status !== 'gone');
  if (!tray.some((entry) => entry.status === 'matching')) {
    compactTraySlots();
  }
  checkEndState();
}

function checkEndState() {
  const visibleTrayCount = traySlotItems.filter(Boolean).length;
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

function updateTimer(now) {
  timeCountEl.textContent = String(Math.floor((now - gameStartTime) / 1000));
}

function updateAnimation(item, now) {
  if (!item.animation) return;
  const progress = THREE.MathUtils.clamp((now - item.animation.start) / item.animation.duration, 0, 1);
  const eased = easeOutCubic(progress);

  if (item.animation.kind === 'moveToTray' || item.animation.kind === 'moveToSlot') {
    item.mesh.position.lerpVectors(item.animation.from, item.animation.to, eased);
    item.mesh.quaternion.slerpQuaternions(item.animation.fromQuaternion, item.animation.toQuaternion, eased);
    item.mesh.scale.setScalar(THREE.MathUtils.lerp(item.animation.startScale, item.animation.endScale, eased));
    if (progress >= 1) {
      item.mesh.quaternion.copy(item.animation.toQuaternion);
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

function randomDirection2() {
  const angle = Math.random() * Math.PI * 2;
  return new THREE.Vector2(Math.cos(angle), Math.sin(angle));
}

function getTraySlotPosition(index) {
  return new THREE.Vector3(
    (index - (traySize - 1) / 2) * trayLayout.spacing,
    trayConfig.y,
    trayConfig.z
  );
}

function updateTrayLayout() {
  if (!camera) return;
  const visibleWidth = camera.right - camera.left;
  const availableWidth = Math.max(visibleWidth - trayConfig.viewportPadding, trayConfig.slotSize);
  const baseWidth = trayConfig.slotSize + trayConfig.spacing * (traySize - 1);
  const slotScale = THREE.MathUtils.clamp(availableWidth / baseWidth, trayConfig.minSlotScale, 1);
  const spacing = trayConfig.spacing * slotScale;

  trayLayout = {
    spacing,
    slotScale,
    itemScale: THREE.MathUtils.lerp(slotScale, 1, 0.35)
  };

  traySlots.forEach((slot, index) => {
    slot.scale.setScalar(slotScale);
    slot.position.copy(getTraySlotPosition(index));
  });
}

function getTrayItemScale(item) {
  return item.baseScale * 0.82 * trayLayout.itemScale;
}

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.classList.remove('hidden');
}

function hideMessage() {
  messageEl.textContent = '';
  messageEl.classList.add('hidden');
}

function tick(now) {
  const delta = Math.min((now - lastTime) / 1000, maxFrameDelta);
  lastTime = now;
  if (!gameOver) updateTimer(now);

  if (world && !gameOver) {
    physicsAccumulator += delta;
    let steps = 0;
    world.timestep = fixedTimeStep;

    while (physicsAccumulator >= fixedTimeStep && steps < maxPhysicsStepsPerFrame) {
      world.step();
      physicsAccumulator -= fixedTimeStep;
      steps += 1;
    }

    if (steps === maxPhysicsStepsPerFrame) {
      physicsAccumulator = 0;
    }
  }

  bodies.forEach((item) => {
    if (item.status === 'gone') return;
    if (item.status === 'active') {
      keepItemInsideCone(item, radiusAtY);
      const pos = item.body.translation();
      const rot = item.body.rotation();
      item.mesh.position.set(pos.x, pos.y, pos.z);
      item.mesh.quaternion.set(rot.x, rot.y, rot.z, rot.w);
    } else {
      updateAnimation(item, now);
    }
  });

  renderer.render(scene, camera);
  animationFrameId = requestAnimationFrame(tick);
}

function resize() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(rect.width, 1);
  const height = Math.max(rect.height, 1);
  renderer.setSize(width, height, false);

  const isNarrowViewport = width < 560;
  const view = isNarrowViewport ? 10.2 : 10.7;
  const aspect = width / height;
  camera.left = -view * aspect * 0.5;
  camera.right = view * aspect * 0.5;
  camera.top = view * 0.5;
  camera.bottom = -view * 0.5;
  camera.updateProjectionMatrix();

  updateTrayLayout();
  layoutTray();
}
