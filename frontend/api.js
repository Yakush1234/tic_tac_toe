export class ApiError extends Error {
  constructor(status) {
    super(`The game API returned HTTP ${status}`);
    this.status = status;
  }
}

async function request(path, body) {
  const options = body === undefined
    ? { cache: "no-store" }
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      };
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new ApiError(response.status);
  }
  return response.json();
}

const gamePath = (id) => `/games/${encodeURIComponent(id)}`;

export const createGame = (settings, previousId) =>
  request("/games", { ...settings, previous_id: previousId });

export const getGame = (id) => request(gamePath(id));

export const sendMove = (id, row, column) =>
  request(`${gamePath(id)}/moves`, { row, column });
