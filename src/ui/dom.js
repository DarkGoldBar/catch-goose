export function createGameDom(app) {
  app.innerHTML = `
    <main class="game-shell">
      <section class="stage-wrap">
        <canvas id="gameCanvas" aria-label="抓大鹅游戏画面"></canvas>
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
    leftCount: app.querySelector('#leftCount'),
    message: app.querySelector('#message'),
    restartButton: app.querySelector('#restartBtn'),
    shuffleButton: app.querySelector('#shuffleBtn'),
    timeCount: app.querySelector('#timeCount')
  };
}