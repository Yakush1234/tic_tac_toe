import { ApiError, createGame, getGame, sendMove } from "/assets/api.js";
import { messages } from "/assets/messages.js";

const form = document.querySelector("#settings");
const languagePicker = document.querySelector("#language-picker");
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
const languageKey = "tic-tac-toe.language";

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

let language = readStorage("localStorage", languageKey) === "en" ? "en" : "ru";
let preferences = loadPreferences();
let gameId = readStorage("sessionStorage", gameKey);
let game = null;
let pending = "";
let needsRefresh = false;
let message = "";

form.elements.namedItem("size").value = String(preferences.size);
form.elements.namedItem("bot_mode").value = preferences.bot_mode;
languagePicker.querySelector(`input[value="${language}"]`).checked = true;

function setGame(snapshot) {
  game = snapshot;
  gameId = snapshot?.game_id ?? null;
  needsRefresh = false;
  writeStorage("sessionStorage", gameKey, gameId);
}

function renderLanguage() {
  const text = messages[language];
  document.documentElement.lang = language;
  document.title = text.title;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = text[element.dataset.i18n];
  }
  for (const element of document.querySelectorAll("[data-i18n-label]")) {
    element.setAttribute("aria-label", text[element.dataset.i18nLabel]);
  }
}

function statusKey() {
  if (pending) return pending;
  if (needsRefresh) return "refreshNeeded";
  if (!game) return "startPrompt";
  if (game.is_draw) return "draw";
  if (game.winner === "human") return "humanWon";
  if (game.winner === "bot") return "botWon";
  return game.current_player === "human" ? "humanTurn" : "botTurn";
}

function canPlay() {
  return !pending && !needsRefresh && game?.current_player === "human";
}

function render() {
  const text = messages[language];
  const nextStatus = text[statusKey()];
  if (status.textContent !== nextStatus) status.textContent = nextStatus;
  const translatedMessage = message ? text[message] : "";
  if (feedback.textContent !== translatedMessage) feedback.textContent = translatedMessage;
  start.disabled = Boolean(pending);
  retry.hidden = !needsRefresh;
  retry.disabled = Boolean(pending);
  assignment.hidden = !game;
  assignment.textContent = game ? text.assignment(game.human_mark) : "";
  gameSettings.hidden = !game;
  gameSettings.textContent = game
    ? `${game.settings.size}×${game.settings.size} · ${text[game.settings.bot_mode === "smart" ? "smartBot" : "randomBot"]}`
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
    cell.setAttribute("aria-label", text.cell(row + 1, column + 1, mark === "E" ? text.empty : mark));
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
      message = "missing";
    } else {
      needsRefresh = true;
      message = "loadFailed";
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

languagePicker.addEventListener("change", (event) => {
  language = event.target.value;
  writeStorage("localStorage", languageKey, language);
  renderLanguage();
  render();
});

form.addEventListener("change", () => {
  const data = new FormData(form);
  preferences = { size: Number(data.get("size")), bot_mode: data.get("bot_mode") };
  writeStorage("localStorage", preferencesKey, JSON.stringify(preferences));
  render();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void run("creating", async () => {
    try {
      setGame(await createGame(preferences, gameId));
    } catch (error) {
      message = error instanceof ApiError && error.status === 503
        ? "busy"
        : "createFailed";
    }
  });
});

board.addEventListener("click", (event) => {
  const cell = event.target.closest("button[data-index]");
  if (!cell || !canPlay() || cell.dataset.mark !== "E") return;
  const size = game.board.length;
  const index = Number(cell.dataset.index);
  void run("moving", async () => {
    try {
      setGame(await sendMove(gameId, Math.floor(index / size), index % size));
    } catch {
      await restoreGame("refreshed");
    }
  });
});

retry.addEventListener("click", () => void run("loading", restoreGame));

renderLanguage();
render();
if (gameId) void run("restoring", restoreGame);
