export interface RankingEntry {
  posicao: number;
  participante_id?: string;
  tag: string;
  nome: string;
  cv?: number | null;
  guerra: number;
  raides: number;
  jogos: number;
  eventos: number;
  total: number;
  temporada?: string;
}

export interface AuditActivity {
  tipo: string;
  identificador: string;
  data: string;
  estado?: string | null;
  temporada?: string | null;
  rodada?: number | null;
  adversario?: string | null;
  jogadores?: number | null;
  ataques?: number | null;
  pontos_competicao?: number | null;
}

export interface AuditActivitiesResponse {
  ok: boolean;
  total: number;
  atividades: AuditActivity[];
}

export interface AttackAudit {
  ordem?: number;
  alvo_nome?: string;
  cv_alvo?: number;
  estrelas?: number;
  percentual?: number;
  pontos?: number;
  tipo?: string;
}

export interface PlayerAuditDetail {
  tag?: string;
  nome?: string;
  cv?: number;
  pontos_competicao?: number;
  pontos_calculados?: number;
  pontos_base?: number;
  motivo?: string;
  atacou?: boolean;
  ataques?: AttackAudit[] | number;
  capital_resources_looted?: number;
  bonus_top3?: number;
}

export interface PlayerAuditRecord extends AuditActivity {
  jogador: PlayerAuditDetail;
}

export interface PlayerAuditResponse {
  ok: boolean;
  player_tag: string;
  total: number;
  pontos_competicao: number;
  registros: PlayerAuditRecord[];
}

export interface LayoutEntry {
  tipo: string;
  cv: string;
  autor: string;
  link: string;
  descricao: string;
  imagem_url: string;
  publicado_em: string;
  tag: string;
}

export interface LayoutsResponse {
  total: number;
  offset: number;
  limit: number;
  layouts: LayoutEntry[];
}

export interface TournamentPlayer {
  tag: string;
  nome: string;
  cv: number;
}

export interface TournamentMatch {
  jogadores: Array<TournamentPlayer | null>;
  vencedor: TournamentPlayer | null;
  automatico?: boolean;
}

export interface TournamentState {
  nome: string;
  clan?: string;
  clan_tag?: string;
  cv: number | "Todos";
  modo: string;
  status: string;
  participantes: TournamentPlayer[];
  rotulos: string[];
  rodadas: TournamentMatch[][];
  campeao: TournamentPlayer | null;
}

export interface TournamentResponse {
  torneio: TournamentState | null;
  roster: {
    clan: string;
    tag: string;
    consultado_em: string;
    contas: TournamentPlayer[];
  } | null;
}

export interface AdminSession {
  autenticado: boolean;
  usuario?: string;
  nivel?: string;
}

export interface AdminSummary {
  admin: { usuario: string; nivel: string };
  temporada: string;
  temporada_nome: string;
  ranking: { jogadores: number; atualizado_em: string };
  participacao: { total: number; habilitadas: number; bloqueadas: number };
  modo: "SOMENTE_LEITURA";
}
