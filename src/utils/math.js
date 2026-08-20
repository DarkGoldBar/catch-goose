export function easeOutCubic(value) {
  return 1 - Math.pow(1 - value, 3);
}

export function randomPointInCircle(radius) {
  const angle = Math.random() * Math.PI * 2;
  const distance = Math.sqrt(Math.random()) * radius;
  return {
    x: Math.cos(angle) * distance,
    z: Math.sin(angle) * distance
  };
}