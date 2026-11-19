import type { PlayerAuditResponse, PlayerFeedback, RankingEntry } from "./types";

export function playerForPeriod(player: RankingEntry, audit: PlayerAuditResponse): PlayerFeedback {
  if (audit.player_tag !== player.tag || !/^\d{4}-(0[1-9]|1[0-2])$/.test(audit.temporada)
      || !audit.resumo || audit.registros.some((r) => r.temporada !== audit.temporada)) {
    throw new Error("O histórico não corresponde ao jogador e ao mês selecionados. Atualize a ficha.");
  }
  // Não reaproveitar pontos/posição do mês atual em uma ficha de outro mês.
  return { ...player, ...audit.resumo, temporada: audit.temporada };
}
