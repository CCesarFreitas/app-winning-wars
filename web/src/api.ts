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
  AdminLayoutDuplicate,
  AdminLayoutDeleteResult,
  AdminContributionRankingResponse,
  AdminDrawRecord,
  AdminDrawResponse,
  AdminMonthCloseResponse,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class LayoutsDuplicadosError extends Error {
  constructor(public itens: AdminLayoutDuplicate[]) {
    super("Alguns layouts deste lote já estão publicados.");
    this.name = "LayoutsDuplicadosError";
  }
}

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
    let detail: unknown = "";
    try { detail = ((await response.json()) as { detail?: unknown }).detail || ""; } catch { /* resposta sem JSON */ }
    if (typeof detail === "object" && detail && (detail as { codigo?: string }).codigo === "layouts_duplicados") {
      throw new LayoutsDuplicadosError(((detail as { itens?: AdminLayoutDuplicate[] }).itens || []));
    }
    const detailMessage = typeof detail === "string" ? detail : "";
    if (response.status === 401) throw new Error("Usuário ou senha inválidos.");
    if (response.status === 429) throw new Error("Muitas tentativas. Aguarde 15 minutos.");
    if (response.status === 426) throw new Error("O login administrativo exige uma conexão HTTPS.");
    if (response.status === 503 && detailMessage === "autenticacao_nao_configurada") throw new Error("A autenticação ainda não foi ativada neste ambiente.");
    throw new Error(detailMessage || `A API respondeu com o código ${response.status}.`);
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
  adminContributionRanking: () => getJson<AdminContributionRankingResponse>("/v1/admin/ranking-contribution"),
  adminDraw: (ranking: "oficial" | "sem_liga") => getJson<AdminDrawResponse>(`/v1/admin/draw?ranking=${ranking}`),
  adminDrawRun: (ranking: "oficial" | "sem_liga", pontos: number, participantes: string[], quantidade: number, sorteio_id: string) =>
    postJson<AdminDrawRecord>("/v1/admin/draw", { ranking, pontos, participantes, quantidade, sorteio_id }),
  adminMonthClose: () => getJson<AdminMonthCloseResponse>("/v1/admin/month-close"),
  adminMonthFinalize: (temporada: string, confirmacao: string) =>
    postJson<{ status: string }>("/v1/admin/month-close/finalize", { temporada, confirmacao }),
  adminMonthOpenNext: (temporada: string, confirmacao: string) =>
    postJson<{ status: string }>("/v1/admin/month-close/open-next", { temporada, confirmacao }),
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
  adminLayoutDelete: (tipo: "Guerra" | "Rankeada", cv: number, link: string) =>
    postJson<AdminLayoutDeleteResult>("/v1/admin/layouts/delete", { tipo, cv, link }),
  adminTournamentStart: (nome: string, modo: string, cv: number | "Todos", tags: string[]) =>
    postJson<AdminWriteResult>("/v1/admin/tournament/start", { nome, modo, cv, tags }),
  adminTournamentWinner: (rodada: number, partida: number, vencedor: string) =>
    postJson<AdminWriteResult>("/v1/admin/tournament/winner", { rodada, partida, vencedor }),
  adminTournamentReset: () => postJson<AdminWriteResult>("/v1/admin/tournament/reset"),
};
