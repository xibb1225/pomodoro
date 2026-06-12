// ============================================
// Pomodoro Timer - Renderer Logic
// ============================================

// ----- Native Bridge Helpers -----
const bridge = {
  hasNative: !!(window.webkit && window.webkit.messageHandlers),

  showNotification(title, body) {
    if (this.hasNative) {
      window.webkit.messageHandlers.notification.postMessage({ title, body });
    }
  },

  setAlwaysOnTop(flag) {
    if (this.hasNative) {
      window.webkit.messageHandlers.alwaysOnTop.postMessage(flag);
    }
  },
};

// Called by Swift when always-on-top is toggled from the menu
function onAlwaysOnTopChanged(flag) {
  const pinToggle = document.getElementById('pinToggle');
  if (pinToggle) pinToggle.checked = flag;
}

// ----- Constants -----
const MODES = {
  work: { name: '专注', icon: '🍅', minutes: 25, color: '#E04D4D', gradient: 'gradient-work' },
  shortBreak: { name: '小休', icon: '☕', minutes: 5, color: '#4ECDC4', gradient: 'gradient-short' },
  longBreak: { name: '长休', icon: '🌿', minutes: 15, color: '#7C8CE0', gradient: 'gradient-long' },
};

const LONG_BREAK_INTERVAL = 4; // every Nth work session → long break

const CIRCUMFERENCE = 2 * Math.PI * 100; // r=100 → ~628.32

// ----- State -----
let currentMode = 'work';
let timeLeft = MODES.work.minutes * 60; // in seconds
let totalTime = MODES.work.minutes * 60;
let isRunning = false;
let timerInterval = null;
let sessionCount = 0;

// ----- DOM Elements -----
const elMinutes = document.querySelector('.timer-minutes');
const elSeconds = document.querySelector('.timer-seconds');
const elSeparator = document.querySelector('.timer-separator');
const elProgressRing = document.querySelector('.ring-progress');
const elTimerContainer = document.querySelector('.timer-container');
const elBtnStart = document.getElementById('btnStart');
const elBtnPause = document.getElementById('btnPause');
const elBtnReset = document.getElementById('btnReset');
const elBtnSkip = document.getElementById('btnSkip');
const elSessionCount = document.getElementById('sessionCount');
const elSessionTomatoes = document.getElementById('sessionTomatoes');
const elPinToggle = document.getElementById('pinToggle');
const elModeTabs = document.querySelectorAll('.mode-tab');

// ----- Audio Engine -----
let audioCtx = null;

// WKWebView suspends AudioContext until a user gesture — prime it on first click
function ensureAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

// Prime audio on any user interaction
document.addEventListener('click', ensureAudioContext, { once: true });
document.addEventListener('keydown', ensureAudioContext, { once: true });

function playAlarm() {
  try {
    const ctx = ensureAudioContext();

    // Pleasant chime melody: ascending then resolving
    const notes = [523, 659, 784, 1047, 784, 1047, 1319, 1568];
    const duration = 0.18;
    const gap = 0.10;

    notes.forEach((freq, i) => {
      const startTime = ctx.currentTime + i * (duration + gap);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.25, startTime);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + duration);
    });
  } catch (e) {
    console.log('Audio unavailable:', e);
  }
}

// ----- Timer Engine -----
function updateDisplay() {
  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const minStr = String(minutes).padStart(2, '0');
  const secStr = String(seconds).padStart(2, '0');

  elMinutes.textContent = minStr;
  elSeconds.textContent = secStr;

  // Update circular progress
  const progress = totalTime > 0 ? timeLeft / totalTime : 1;
  const offset = CIRCUMFERENCE * (1 - progress);
  elProgressRing.style.strokeDashoffset = offset;

  // Blinking separator when running
  elSeparator.classList.toggle('paused', !isRunning);

  // Update window title (reflected in the window chrome / dock)
  const mode = MODES[currentMode];
  document.title = `${mode.icon} ${minStr}:${secStr} - ${mode.name}`;
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  isRunning = false;
  elBtnStart.classList.remove('hidden');
  elBtnPause.classList.add('hidden');
}

function startTimer() {
  if (isRunning) return;
  isRunning = true;

  elBtnStart.classList.add('hidden');
  elBtnPause.classList.remove('hidden');

  tick();
  timerInterval = setInterval(tick, 1000);
  updateDisplay();
}

function tick() {
  timeLeft--;

  if (timeLeft <= 0) {
    timeLeft = 0;
    clearInterval(timerInterval);
    timerInterval = null;
    isRunning = false;
    timerFinished();
  }

  updateDisplay();
}

function pauseTimer() {
  if (!isRunning) return;
  stopTimer();
  updateDisplay();
}

function resetTimer() {
  stopTimer();
  timeLeft = MODES[currentMode].minutes * 60;
  totalTime = MODES[currentMode].minutes * 60;
  elTimerContainer.classList.remove('finished');
  updateDisplay();
}

function timerFinished() {
  elBtnStart.classList.remove('hidden');
  elBtnPause.classList.add('hidden');
  elTimerContainer.classList.add('finished');

  // Sound + notification
  playAlarm();

  const modeName = MODES[currentMode].name;
  bridge.showNotification(
    '⏰ 番茄钟',
    currentMode === 'work'
      ? `「${modeName}」结束，该休息了 ☕`
      : `「${modeName}」结束，开始新的番茄 🍅`
  );

  // Count completed work sessions
  if (currentMode === 'work') {
    sessionCount++;
    updateSessionDisplay();
  }

  // Automatically advance to next phase
  autoSwitch();
}

function autoSwitch() {
  if (currentMode === 'work') {
    // Every Nth work session → long break
    if (sessionCount > 0 && sessionCount % LONG_BREAK_INTERVAL === 0) {
      switchMode('longBreak');
    } else {
      switchMode('shortBreak');
    }
  } else {
    switchMode('work');
  }
}

function switchMode(mode) {
  currentMode = mode;
  timeLeft = MODES[mode].minutes * 60;
  totalTime = MODES[mode].minutes * 60;

  // Halt any running session
  stopTimer();

  // Update mode tabs
  elModeTabs.forEach(tab => {
    tab.classList.toggle('active', tab.dataset.mode === mode);
  });

  // Update the ring to use the right gradient
  elTimerContainer.dataset.mode = mode;
  elProgressRing.setAttribute('stroke', `url(#${MODES[mode].gradient})`);
  elProgressRing.style.strokeDashoffset = '0';
  elTimerContainer.classList.remove('finished');

  updateDisplay();
}

function skipToNext() {
  stopTimer();
  autoSwitch();
}

// ----- Session Display -----
function updateSessionDisplay() {
  elSessionCount.textContent = sessionCount;

  const maxDots = 16;
  const show = Math.min(sessionCount, maxDots);
  let html = '';
  for (let i = 0; i < show; i++) {
    html += '<span class="tomato-dot"></span>';
  }
  if (sessionCount > maxDots) {
    html += `<span style="font-size:11px;color:var(--text-secondary);margin-left:4px;">+${sessionCount - maxDots}</span>`;
  }
  elSessionTomatoes.innerHTML = html;
}

// ----- Event Bindings -----
elBtnStart.addEventListener('click', startTimer);
elBtnPause.addEventListener('click', pauseTimer);
elBtnReset.addEventListener('click', resetTimer);
elBtnSkip.addEventListener('click', skipToNext);

elModeTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const mode = tab.dataset.mode;
    if (mode !== currentMode) switchMode(mode);
  });
});

elPinToggle.addEventListener('change', () => {
  bridge.setAlwaysOnTop(elPinToggle.checked);
});

// ----- Keyboard Shortcuts -----
document.addEventListener('keydown', (e) => {
  // Ignore when typing in an input
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  // Don't swallow Cmd+key combos (menu bar)
  if (e.metaKey) return;

  switch (e.code) {
    case 'Space':
      e.preventDefault();
      isRunning ? pauseTimer() : startTimer();
      break;
    case 'KeyR':
      resetTimer();
      break;
    case 'KeyS':
      skipToNext();
      break;
    case 'Digit1':
      switchMode('work');
      break;
    case 'Digit2':
      switchMode('shortBreak');
      break;
    case 'Digit3':
      switchMode('longBreak');
      break;
  }
});

// ----- Init -----
function init() {
  elTimerContainer.dataset.mode = 'work';
  elProgressRing.style.strokeDasharray = CIRCUMFERENCE;
  elProgressRing.style.strokeDashoffset = '0';
  updateDisplay();
  updateSessionDisplay();
}

init();

console.log('🍅 番茄钟已就绪');
console.log('  Space → 开始/暂停');
console.log('  R → 重置');
console.log('  S → 跳过');
console.log('  1/2/3 → 切换模式');
