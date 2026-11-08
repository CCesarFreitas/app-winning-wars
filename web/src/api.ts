import type {
  AuditActivitiesResponse,
  PlayerAuditResponse,
  RankingEntry,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

async function getJson<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 12_000);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`A API respondeu com o código ${response.status}.`);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("A consulta demorou mais de 12 segundos.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  ranking: () => getJson<RankingEntry[]>("/v1/ranking"),
  atividades: (limite = 50) =>
    getJson<AuditActivitiesResponse>(`/audit/activities?limite=${limite}`),
  jogador: (tag: string, limite = 100) =>
    getJson<PlayerAuditResponse>(
      `/audit/player/${encodeURIComponent(tag)}?limite=${limite}`,
    ),
};
