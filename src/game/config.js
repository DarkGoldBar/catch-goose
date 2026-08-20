export const traySize = 7;

export const cone = {
  topY: 6,
  bottomY: -4,
  topRadius: 4,
  bottomRadius: 0.5,
  capPadding: 0.5,
  itemRadius: 0.3
};

export const trayConfig = {
  y: 0.35,
  z: 4.35,
  spacing: 0.82,
  slotSize: 0.68,
  minSlotScale: 0.58,
  viewportPadding: 0.45
};

export const initialItemCount = 99;
export const modelDisplayScale = 1.2;
export const colliderPadding = 0.08;
export const ellipsoidLatitudeSegments = 6;
export const ellipsoidLongitudeSegments = 12;
export const fixedTimeStep = 1 / 60;
export const maxFrameDelta = 0.1;
export const maxPhysicsStepsPerFrame = 4;
export const trayEulerArgs = [-Math.PI / 5, Math.PI / 4, -Math.PI / 12, 'XYZ'];
