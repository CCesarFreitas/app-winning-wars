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

export interface RankingDetailColumn {
  chave: string;
  rotulo: string;
  tipo: "guerra" | "liga" | "raide" | "jogos" | "eventos";
}

export interface RankingDetailEntry extends RankingEntry {
  pontos: Record<string, number>;
}

export interface RankingDetailsResponse {
  temporada: string;
  temporada_nome: string;
  atualizado_em: string;
  total: number;
  colunas: RankingDetailColumn[];
  jogadores: RankingDetailEntry[];
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

export interface AdminLayoutDuplicate {
  linha_lote: number;
  link: string;
  tipo: string;
  cv: string;
  autor: string;
  publicado_em: string;
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

export interface ClanResponse {
  nome: string;
  tag: string;
  nivel?: number | null;
  membros: number;
  consultado_em: string;
}

export interface PlanningMember {
  tag: string;
  name: string;
  townHallLevel?: number;
  townhallLevel?: number;
  mapPosition?: number;
  attacks?: PlanningAttack[];
}

export interface PlanningAttack {
  stars: number;
  destructionPercentage: number;
  duration?: number;
  attackerTag: string;
  defenderTag: string;
}

export interface PlanningClan {
  tag: string;
  name: string;
  members: PlanningMember[];
  attacks?: number;
  stars?: number;
  destructionPercentage?: number;
}

export interface PlanningWar {
  state: string;
  teamSize: number;
  startTime: string;
  endTime: string;
  clan: PlanningClan;
  opponent: PlanningClan;
}

export interface PlanningEnvelope {
  consultado_em: string;
  dados: PlanningWar;
  tipo?: string;
  rodada?: number;
  warTag?: string;
  temporada?: string;
}

export interface PlanningGroup {
  state: string;
  season: string;
  clans: PlanningClan[];
  rounds: Array<{ warTags: string[] }>;
}

export interface PlanningResponse {
  versao: number;
  publicado_em: string;
  grupo: { consultado_em: string; dados: PlanningGroup } | null;
  comum: PlanningEnvelope | null;
  guerras_liga: PlanningEnvelope[];
  historico_comum: PlanningEnvelope[];
  pendencias: string[];
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
  modo: "SOMENTE_LEITURA" | "LEITURA_E_ESCRITA";
}

export interface AdminParticipationAccount {
  tag: string;
  nome: string;
  pontos: number;
  inscrita: boolean;
  habilitada?: "TRUE" | "FALSE" | null;
  origem_decisao?: string | null;
  situacao: "MEMBRO_ATUAL" | "AUSENTE_AGORA" | "RETORNOU_AO_CLA" | "ENTROU_APOS_INICIO_DO_HISTORICO" | "SEM_REGISTRO_NO_CLA";
  no_cla: boolean;
  primeira_vista?: string | null;
  ultima_vista?: string | null;
  participante_id?: string | null;
  cv?: number | null;
  cargo?: string | null;
  administrador?: string;
  motivo?: string;
  decidido_em?: string;
  evento_id?: string;
  contribuicao?: {
    guerra: number;
    raides: number;
    jogos: number;
    eventos: number;
    total: number;
    atividades: number;
  };
}

export interface AdminParticipationResponse {
  temporada: string;
  temporada_nome: string;
  consultado_em: string;
  roster_em: string;
  criterio: string;
  contagens: {
    total: number;
    no_cla: number;
    ausentes: number;
    habilitadas: number;
    bloqueadas: number;
    sem_decisao: number;
    inscritas: number;
    com_pontos: number;
  };
  contas: AdminParticipationAccount[];
}

export interface AdminManualAccount {
  tag: string;
  nome: string;
  cv?: number | null;
  participante_id?: string | null;
  habilitada?: "TRUE" | "FALSE" | null;
  inscrita: boolean;
  no_cla: boolean;
  jogos: number;
  eventos: number;
}

export interface AdminManualHistory {
  EventoID: string;
  Temporada: string;
  PlayerTag: string;
  ParticipanteID: string;
  Atividade: "JogosCla" | "Eventos";
  ValorInformado: string;
  Antes: string;
  Depois: string;
  Administrador: string;
  RegistradoEm: string;
}

export interface AdminManualResponse {
  temporada: string;
  temporada_nome: string;
  regras: { jogos: string; operacao: string };
  contas: AdminManualAccount[];
  historico: AdminManualHistory[];
  modo: "SOMENTE_LEITURA";
}

export interface AdminManualProposal {
  status: "BLOQUEADO" | "ZERO_SEM_INSCRICAO" | "PROPOSTA_SEM_ENVIO";
  motivo?: string;
  conta: AdminManualAccount;
  atividade: "JogosCla" | "Eventos";
  informado: number;
  antes: number;
  depois: number;
  inscreveria: boolean;
}

export interface AdminWriteResult {
  status: string;
  tag?: string;
  habilitada?: boolean;
  evento_id?: string;
  aplicados?: number;
  ignorados?: number;
  resultados?: Array<{ tag: string; antes: number; depois: number }>;
}

export interface AdminLayoutItemInput {
  link: string;
  descricao: string;
  imagem_url: string;
  imagem_base64: string;
}

export interface AdminLayoutsResult extends AdminWriteResult {
  aplicados: number;
  tipo: "Guerra" | "Rankeada";
  cv: number;
  backup: string;
}

export interface AdminLayoutDeleteResult extends AdminWriteResult {
  removidos: number;
  link: string;
  tipo: "Guerra" | "Rankeada";
  cv: number;
  backup: string;
  imagem_externa_preservada: boolean;
}
