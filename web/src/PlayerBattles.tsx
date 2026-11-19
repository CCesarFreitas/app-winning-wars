import type { PlayerAuditResponse } from './types';
import { battlePerformance, leagueRounds, percent } from './playerPerformance';

export function PlayerBattles({ audit }: { audit: PlayerAuditResponse }) {
  return <section className="battle-performance" aria-label="Desempenho separado por modalidade">
    {(['liga', 'guerra'] as const).map(type => {
      const s = battlePerformance(audit.registros, type);
      return <article className="battle-panel" key={type}>
        <h2>{type === 'liga' ? 'Liga · desempenho nas rodadas' : 'Guerras comuns'}</h2>
        <p>{type === 'liga' ? 'Apenas rodadas encerradas em que a vila foi escalada. Reserva não é falta.' : 'Somente guerras encerradas com a vila na escalação.'}</p>
        <div className="battle-metrics">
          <div><strong>{s.activities.length}</strong><span>{type === 'liga' ? 'rodadas escaladas' : 'guerras escaladas'}</span></div>
          <div><strong>{s.attacks.length}</strong><span>ataques feitos</span></div>
          <div><strong>{s.noAttack}</strong><span>{type === 'liga' ? 'rodadas sem atacar' : 'guerras sem atacar'}</span></div>
          <div><strong>{s.missing ?? '—'}</strong><span>ataques não usados</span></div>
          <div><strong>{percent(s.tripleRate)}</strong><span>3★ por ataque com estrelas registradas</span></div>
          <div><strong>{s.average?.toFixed(2) ?? '—'}</strong><span>média de estrelas por ataque</span></div>
        </div>
        <div className="star-distribution" aria-label="Distribuição das estrelas">
          {[3, 2, 1, 0].map(n => <div key={n}><span>{n}★</span><meter min={0} max={Math.max(1, s.attacks.length)} value={s.distribution[n]} /><strong>{s.distribution[n]}</strong></div>)}
        </div>
        <small>Taxas calculadas sobre ataques com estrelas registradas; não atacar é mostrado separadamente. {s.unknown > 0 ? `${s.unknown} registro(s) incompleto(s).` : ''}</small>
        {type === 'liga' && <>
          <div className="league-rounds">{leagueRounds(audit.registros, audit.liga_rodadas_disponiveis).map(r => <div key={r.round}><small>Rodada {r.round}</small><strong>{r.label}</strong>{r.record && Array.isArray(r.record.jogador.ataques) && r.record.jogador.ataques.map((a, i) => <small key={i}>CV {a.cv_atacante ?? r.record?.jogador.cv ?? '?'} → CV {a.cv_alvo ?? '?'} · {a.percentual ?? '?'}%</small>)}</div>)}</div>
          <small>“Sem registro” não indica reserva nem falta. Compare meses e níveis dos alvos antes de definir titulares; poucas rodadas representam uma amostra menor.</small>
        </>}
      </article>;
    })}
  </section>;
}
