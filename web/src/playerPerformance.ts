import type { PlayerAuditRecord } from './types';

export function battlePerformance(records: PlayerAuditRecord[], type: 'guerra' | 'liga') {
  const activities = [...new Map(records.filter(r => r.tipo === type).map(r => [r.identificador, r])).values()];
  const known = activities.filter(r => Array.isArray(r.jogador.ataques));
  const attacks = known.flatMap(r => Array.isArray(r.jogador.ataques) ? r.jogador.ataques : []);
  const stars = attacks.map(a => a.estrelas).filter((s): s is number => Number.isInteger(s) && s! >= 0 && s! <= 3);
  const distribution = [0, 1, 2, 3].map(n => stars.filter(s => s === n).length);
  const missing = known.reduce((sum, r) => {
    const limit = type === 'liga' ? 1 : r.jogador.limite_ataques;
    return sum + (typeof limit === 'number' ? Math.max(0, limit - (r.jogador.ataques as unknown[]).length) : 0);
  }, 0);
  const complete = known.length === activities.length && (type === 'liga' || known.every(r => typeof r.jogador.limite_ataques === 'number'));
  return {
    activities, attacks, distribution, missing: complete ? missing : null,
    noAttack: known.filter(r => (r.jogador.ataques as unknown[]).length === 0).length,
    used: known.filter(r => (r.jogador.ataques as unknown[]).length > 0).length,
    average: stars.length ? stars.reduce((a, b) => a + b, 0) / stars.length : null,
    tripleRate: stars.length ? 100 * distribution[3] / stars.length : null,
    unknown: attacks.length - stars.length + activities.length - known.length,
    points: activities.reduce((sum, r) => sum + (r.jogador.pontos_competicao ?? 0), 0),
  };
}

export const percent = (value: number | null) => value == null ? '—' : `${value.toFixed(1)}%`;

export function leagueRounds(records: PlayerAuditRecord[], available: number[] = []) {
  return Array.from({ length: 7 }, (_, i) => {
    const round = i + 1;
    const record = records.find(r => r.tipo === 'liga' && r.rodada === round);
    const attacks = record && Array.isArray(record.jogador.ataques) ? record.jogador.ataques : null;
    const label = record ? attacks ? attacks.length ? attacks.map(a => `${a.estrelas ?? '?'}★`).join(' / ') : 'Não atacou' : 'Ataque indisponível' : available.includes(round) ? 'Não escalado' : 'Sem registro';
    return { round, record, label };
  });
}
