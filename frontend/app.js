import { ApiError, createGame, getGame, sendMove } from "/assets/api.js";

const form = document.querySelector("#settings");
const board = document.querySelector("#board");
const status = document.querySelector("#status");
const assignment = document.querySelector("#assignment");
const gameSettings = document.querySelector("#game-settings");
const settingsNote = document.querySelector("#settings-note");
const feedback = document.querySelector("#feedback");
const start = document.querySelector("#start");
const retry = document.querySelector("#retry");

const preferencesKey = "tic-tac-toe.preferences";
const gameKey = "tic-tac-toe.game-id";
const marks = { X: "×", O: "○", E: "" };
const modeNames = { random: "Случайный бот", smart: "Продуманный бот" };

function readStorage(scope, key) {
  try {
    return window[scope].getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(scope, key, value) {
  try {
    if (value === null) window[scope].removeItem(key);
    else window[scope].setItem(key, value);
  } catch {
    // The active game still works when browser storage is unavailable.
  }
}

function loadPreferences() {
  try {
    const saved = JSON.parse(readStorage("localStorage", preferencesKey));
    return {
      size: [3, 4, 5].includes(saved?.size) ? saved.size : 3,
      bot_mode: ["random", "smart"].includes(saved?.bot_mode) ? saved.bot_mode : "random",
    };
  } catch {
    return { size: 3, bot_mode: "random" };
  }
}

let preferences = loadPreferences();
let gameId = readStorage("sessionStorage", gameKey);
let game = null;
let pending = "";
let needsRefresh = false;
let message = "";

form.elements.namedItem("size").value = String(preferences.size);
form.elements.namedItem("bot_mode").value = preferences.bot_mode;

function setGame(snapshot) {
  game = snapshot;
  gameId = snapshot?.game_id ?? null;
  needsRefresh = false;
  writeStorage("sessionStorage", gameKey, gameId);
}

function statusText() {
  if (pending) return pending;
  if (needsRefresh) return "Нужно обновить поле";
  if (!game) return "Начните новую игру";
  if (game.is_draw) return "Ничья";
  if (game.winner === "human") return "Вы победили";
  if (game.winner === "bot") return "Бот победил";
  return game.current_player === "human" ? "Ваш ход" : "Ход бота";
}

function canPlay() {
  return !pending && !needsRefresh && game?.current_player === "human";
}

function render() {
  const nextStatus = statusText();
  if (status.textContent !== nextStatus) status.textContent = nextStatus;
  if (feedback.textContent !== message) feedback.textContent = message;
  start.disabled = Boolean(pending);
  retry.hidden = !needsRefresh;
  retry.disabled = Boolean(pending);
  assignment.hidden = !game;
  assignment.textContent = game ? `Вы играете за ${game.human_mark}` : "";
  gameSettings.hidden = !game;
  gameSettings.textContent = game
    ? `${game.settings.size}×${game.settings.size} · ${modeNames[game.settings.bot_mode]}`
    : "";
  settingsNote.hidden = !game;
  board.setAttribute("aria-busy", String(Boolean(pending)));

  const size = game?.board.length ?? preferences.size;
  if (board.childElementCount !== size * size) {
    board.style.setProperty("--size", size);
    const cells = document.createDocumentFragment();
    for (let index = 0; index < size * size; index += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.index = String(index);
      cells.append(cell);
    }
    board.replaceChildren(cells);
  }

  const playable = canPlay();
  const activeCell = board.contains(document.activeElement) ? document.activeElement : null;
  for (const [index, cell] of Array.from(board.children).entries()) {
    const row = Math.floor(index / size);
    const column = index % size;
    const mark = game?.board[row][column] ?? "E";
    cell.dataset.mark = mark;
    cell.textContent = marks[mark];
    cell.setAttribute("aria-label", `Строка ${row + 1}, столбец ${column + 1}, ${mark === "E" ? "пусто" : mark}`);
    cell.disabled = !game;
    cell.setAttribute("aria-disabled", String(!playable || mark !== "E"));
    cell.tabIndex = playable && mark === "E" ? 0 : -1;
  }
  if (!pending && activeCell && (activeCell.tabIndex < 0 || !activeCell.isConnected)) {
    (board.querySelector('[tabindex="0"]') ?? status).focus();
  }
}

async function restoreGame(successMessage = "") {
  try {
    setGame(await getGame(gameId));
    message = successMessage;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      setGame(null);
      message = "Партия больше недоступна. Можно начать новую.";
    } else {
      needsRefresh = true;
      message = "Не удалось загрузить поле. Попробуйте ещё раз.";
    }
  }
}

async function run(label, operation) {
  if (pending) return;
  pending = label;
  message = "";
  render();
  try {
    await operation();
  } finally {
    pending = "";
    render();
  }
}

form.addEventListener("change", () => {
  const data = new FormData(form);
  preferences = { size: Number(data.get("size")), bot_mode: data.get("bot_mode") };
  writeStorage("localStorage", preferencesKey, JSON.stringify(preferences));
  render();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void run("Создаём партию…", async () => {
    try {
      setGame(await createGame(preferences, gameId));
    } catch (error) {
      message = error instanceof ApiError && error.status === 503
        ? "Сервер занят. Попробуйте начать игру позже."
        : "Не удалось начать новую игру. Попробуйте ещё раз.";
    }
  });
});

board.addEventListener("click", (event) => {
  const cell = event.target.closest("button[data-index]");
  if (!cell || !canPlay() || cell.dataset.mark !== "E") return;
  const size = game.board.length;
  const index = Number(cell.dataset.index);
  void run("Обрабатываем ход…", async () => {
    try {
      setGame(await sendMove(gameId, Math.floor(index / size), index % size));
    } catch {
      await restoreGame("Поле обновлено. Проверьте позицию перед следующим ходом.");
    }
  });
});

retry.addEventListener("click", () => void run("Загружаем поле…", restoreGame));

render();
if (gameId) void run("Восстанавливаем партию…", restoreGame);
