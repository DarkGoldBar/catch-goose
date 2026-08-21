export function createGameDom(app) {
  app.innerHTML = `
    <main class="game-shell">
      <section class="stage-wrap">
        <canvas id="gameCanvas" aria-label="抓大鹅游戏画面"></canvas>
        <section id="loadingScreen" class="loading-screen" aria-live="polite">
          <div id="versionBadge" class="version-badge"></div>
          <div class="loading-panel">
            <p class="loading-kicker">抓大鹅</p>
            <h1 id="loadingTitle">正在准备游戏</h1>
            <p id="loadingStatus">正在加载游戏资源</p>
            <div class="loading-track" role="progressbar" aria-label="游戏加载进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
              <span id="loadingProgress"></span>
            </div>
            <p id="loadingCount">0%</p>
            <div id="loadingError" class="loading-error hidden">
              <p>资源加载失败，请检查网络后重试。</p>
              <button id="loadingRetry" type="button">重新加载</button>
            </div>
          </div>
        </section>
        <div class="left-hud">
          <div class="left-badge">剩余 <strong id="leftCount">0</strong></div>
          <button id="shuffleBtn" type="button">晃一下</button>
        </div>
        <div class="right-hud">
          <div class="time-badge">时间 <strong id="timeCount">0</strong>s</div>
          <button id="restartBtn" class="restart-button" type="button">重新开始</button>
        </div>
        <div id="message" class="message hidden"></div>
      </section>
    </main>
  `;

  return {
    canvas: app.querySelector('#gameCanvas'),
    loadingCount: app.querySelector('#loadingCount'),
    loadingError: app.querySelector('#loadingError'),
    loadingProgress: app.querySelector('#loadingProgress'),
    loadingRetry: app.querySelector('#loadingRetry'),
    loadingScreen: app.querySelector('#loadingScreen'),
    loadingStatus: app.querySelector('#loadingStatus'),
    loadingTitle: app.querySelector('#loadingTitle'),
    loadingTrack: app.querySelector('.loading-track'),
    leftCount: app.querySelector('#leftCount'),
    message: app.querySelector('#message'),
    restartButton: app.querySelector('#restartBtn'),
    shuffleButton: app.querySelector('#shuffleBtn'),
    timeCount: app.querySelector('#timeCount'),
    versionBadge: app.querySelector('#versionBadge')
  };
}