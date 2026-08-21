import catalog from '../../assets/item-catalog.json';

const modelFiles = import.meta.glob('../../assets/models/**/*.glb', {
  eager: true,
  import: 'default',
  query: '?url'
});
const backgroundFiles = import.meta.glob('../../assets/backgrounds/*.png', {
  eager: true,
  import: 'default',
  query: '?url'
});

const modelUrlByCatalogPath = Object.fromEntries(
  Object.entries(modelFiles).map(([path, url]) => [path.replace('../../', ''), url])
);
const backgroundUrlByCatalogPath = Object.fromEntries(
  Object.entries(backgroundFiles).map(([path, url]) => [path.replace('../../', ''), url])
);

export function getAllGameAssetUrls() {
  return [
    ...Object.values(modelFiles),
    ...Object.values(backgroundFiles),
  ];
}

export function getRandomTheme() {
  const { themes } = catalog;
  return themes[Math.floor(Math.random() * themes.length)] || null;
}

export function getDefaultTheme() {
  return catalog.themes[0];
}

export function getThemeById(id) {
  return catalog.themes.find((theme) => theme.id === id) || null;
}

export function getThemeBackgroundUrl(theme) {
  return theme?.background ? backgroundUrlByCatalogPath[theme.background] : null;
}

export function getThemeItemTypes(theme) {
  return theme.items.map((item) => ({
    id: item.id,
    name: item.name,
    modelUrl: modelUrlByCatalogPath[item.model],
    modelScale: getCatalogModelScale(item)
  }));
}

function getCatalogModelScale(item) {
  const scale = Number(item.scale);
  return Number.isFinite(scale) && scale > 0 ? scale : 1;
}
