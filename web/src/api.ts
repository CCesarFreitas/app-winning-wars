import type {
  AuditActivitiesResponse,
  AdminSession,
  AdminSummary,
  AdminParticipationResponse,
  LayoutsResponse,
  PlayerAuditResponse,
  RankingEntry,
  TournamentResponse,
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

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Usuário ou senha inválidos.");
    if (response.status === 429) throw new Error("Muitas tentativas. Aguarde 15 minutos.");
    if (response.status === 426) throw new Error("O login administrativo exige uma conexão HTTPS.");
    if (response.status === 503) throw new Error("A autenticação ainda não foi ativada neste ambiente.");
    throw new Error(`A API respondeu com o código ${response.status}.`);
  }
  return (await response.json()) as T;
}

export const api = {
  ranking: () => getJson<RankingEntry[]>("/v1/ranking"),
  atividades: (limite = 50) =>
    getJson<AuditActivitiesResponse>(`/audit/activities?limite=${limite}`),
  jogador: (tag: string, limite = 100) =>
    getJson<PlayerAuditResponse>(
      `/audit/player/${encodeURIComponent(tag)}?limite=${limite}`,
    ),
  layouts: (tipo: string, cv?: string, limit = 12, offset = 0) => {
    const params = new URLSearchParams({ tipo, limit: String(limit), offset: String(offset) });
    if (cv) params.set("cv", cv);
    return getJson<LayoutsResponse>(`/v1/layouts?${params.toString()}`);
  },
  torneio: () => getJson<TournamentResponse>("/v1/tournament"),
  adminSession: () => getJson<AdminSession>("/v1/admin/session"),
  adminLogin: (usuario: string, senha: string) =>
    postJson<AdminSession>("/v1/admin/login", { usuario, senha }),
  adminLogout: () => postJson<AdminSession>("/v1/admin/logout"),
  adminSummary: () => getJson<AdminSummary>("/v1/admin/summary"),
  adminParticipation: () => getJson<AdminParticipationResponse>("/v1/admin/participation"),
};
