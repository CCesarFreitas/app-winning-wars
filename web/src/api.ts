import type {
  AuditActivitiesResponse,
  AdminSession,
  AdminSummary,
  AdminParticipationResponse,
  AdminManualProposal,
  AdminManualResponse,
  LayoutsResponse,
  PlayerAuditResponse,
  RankingEntry,
  RankingDetailsResponse,
  TournamentResponse,
  ClanResponse,
  PlanningResponse,
  AdminWriteResult,
  AdminLayoutItemInput,
  AdminLayoutsResult,
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
    let detail = "";
    try { detail = String(((await response.json()) as { detail?: string }).detail || ""); } catch { /* resposta sem JSON */ }
    if (response.status === 401) throw new Error("Usuário ou senha inválidos.");
    if (response.status === 429) throw new Error("Muitas tentativas. Aguarde 15 minutos.");
    if (response.status === 426) throw new Error("O login administrativo exige uma conexão HTTPS.");
    if (response.status === 503 && detail === "autenticacao_nao_configurada") throw new Error("A autenticação ainda não foi ativada neste ambiente.");
    throw new Error(detail || `A API respondeu com o código ${response.status}.`);
  }
  return (await response.json()) as T;
}

export const api = {
  ranking: () => getJson<RankingEntry[]>("/v1/ranking"),
  rankingDetails: () => getJson<RankingDetailsResponse>("/v1/ranking/details"),
  atividades: (limite = 50) =>
    getJson<AuditActivitiesResponse>(`/v1/admin/audit/activities?limite=${limite}`),
  jogador: (tag: string, limite = 100) =>
    getJson<PlayerAuditResponse>(
      `/v1/admin/audit/player/${encodeURIComponent(tag)}?limite=${limite}`,
    ),
  layouts: (tipo: string, cv?: string, limit = 12, offset = 0) => {
    const params = new URLSearchParams({ tipo, limit: String(limit), offset: String(offset) });
    if (cv) params.set("cv", cv);
    return getJson<LayoutsResponse>(`/v1/layouts?${params.toString()}`);
  },
  torneio: () => getJson<TournamentResponse>("/v1/tournament"),
  clan: () => getJson<ClanResponse>("/v1/clan"),
  planning: () => getJson<PlanningResponse>("/v1/planning"),
  adminSession: () => getJson<AdminSession>("/v1/admin/session"),
  adminLogin: (usuario: string, senha: string) =>
    postJson<AdminSession>("/v1/admin/login", { usuario, senha }),
  adminLogout: () => postJson<AdminSession>("/v1/admin/logout"),
  adminSummary: () => getJson<AdminSummary>("/v1/admin/summary"),
  adminParticipation: () => getJson<AdminParticipationResponse>("/v1/admin/participation"),
  adminParticipationToggle: (tag: string, habilitada: boolean, motivo: string, evento_anterior: string) =>
    postJson<AdminWriteResult>("/v1/admin/participation/toggle", { tag, habilitada, motivo, evento_anterior }),
  adminManual: () => getJson<AdminManualResponse>("/v1/admin/manual"),
  adminManualProposal: (tag: string, atividade: "JogosCla" | "Eventos", valor: number) =>
    postJson<AdminManualProposal>("/v1/admin/manual/proposal", { tag, atividade, valor }),
  adminManualBatch: (atividade: "JogosCla" | "Eventos", entradas: Array<{ tag: string; nome: string; valor: number }>) =>
    postJson<AdminWriteResult>("/v1/admin/manual/batch", { atividade, entradas }),
  adminLayoutsBatch: (tipo: "Guerra" | "Rankeada", cv: number, itens: AdminLayoutItemInput[]) =>
    postJson<AdminLayoutsResult>("/v1/admin/layouts/batch", { tipo, cv, itens }),
  adminTournamentStart: (nome: string, modo: string, cv: number | "Todos", tags: string[]) =>
    postJson<AdminWriteResult>("/v1/admin/tournament/start", { nome, modo, cv, tags }),
  adminTournamentWinner: (rodada: number, partida: number, vencedor: string) =>
    postJson<AdminWriteResult>("/v1/admin/tournament/winner", { rodada, partida, vencedor }),
  adminTournamentReset: () => postJson<AdminWriteResult>("/v1/admin/tournament/reset"),
};
