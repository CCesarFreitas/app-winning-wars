export interface RankingEntry {
  posicao: number;
  tag: string;
  nome: string;
  guerra: number;
  raides: number;
  jogos: number;
  eventos: number;
  total: number;
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
