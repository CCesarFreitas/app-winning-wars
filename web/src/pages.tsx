import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";
import { ErrorState, Loading, PageHeader, PlayerAvatar } from "./components";
import { dataAtividade, numero, rotuloTipo, temporadaLabel } from "./format";
import { useRanking } from "./RankingContext";
import type { AuditActivity, PlayerAuditResponse } from "./types";
import { CREST_URL } from "./assets";

export function HomePage() {
  const { ranking, loading, error, recarregar } = useRanking();
  const lider = ranking[0];
  const pontos = ranking.reduce((total, player) => total + player.total, 0);
  const temporada = temporadaLabel(lider?.temporada);

  return (
    <div className="page home-page">
      <section className="hero">
        <div className="hero-copy">
          <span className="battle-status"><i className="live-dot" /> Temporada em disputa · {temporada}</span>
          <h1>Toda batalha conta.<br /><em>Toda vitória deixa um legado.</em></h1>
          <p>A arena oficial da competição Winning Wars. Acompanhe sua evolução, confira cada ponto e lute pelo topo do clã.</p>
          <div className="hero-actions">
            <Link className="primary-button" to="/ranking"><span>♛</span> Entrar no ranking</Link>
            <Link className="secondary-button" to="/auditoria">Ver batalhas encerradas <span>→</span></Link>
          </div>
        </div>
        <div className="hero-emblem" aria-hidden="true">
          <span className="emblem-glow" />
          <img src={CREST_URL} alt="" />
          <div className="clan-level"><small>Nível do clã</small><strong>18</strong></div>
        </div>
      </section>

      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={recarregar} />}
      {!loading && !error && (
        <>
          <section className="stat-grid" aria-label="Resumo da competição">
            <article className="stat-card"><span className="stat-icon">⚔</span><div><small>Guerreiros na disputa</small><strong>{numero(ranking.length)}</strong><span>competidores oficiais</span></div></article>
            <article className="stat-card"><span className="stat-icon">✦</span><div><small>Pontos conquistados</small><strong>{numero(pontos)}</strong><span>nesta temporada</span></div></article>
            <article className="stat-card accent"><span className="stat-icon">♛</span><div><small>Líder da temporada</small><strong>{lider?.nome || "—"}</strong><span>{lider ? `${lider.total} pontos` : "Ranking vazio"}</span></div></article>
          </section>

          <section className="section-block">
            <div className="section-title"><div><span className="eyebrow">Salão dos campeões</span><h2>O pódio da temporada</h2><p>Os guerreiros que comandam a disputa neste momento.</p></div><Link to="/ranking">Ver classificação completa →</Link></div>
            <div className="podium-grid">
              {ranking.slice(0, 3).map((player) => (
                <Link to={`/jogador/${encodeURIComponent(player.tag)}`} className={`podium-card place-${player.posicao}`} key={player.tag}>
                  <span className="place-badge">{player.posicao}º</span>
                  <PlayerAvatar nome={player.nome} position={player.posicao} />
                  <div><strong>{player.nome}</strong><small>{player.tag}</small></div>
                  <b>{player.total}<small> pts</small></b>
                </Link>
              ))}
            </div>
          </section>
          <section className="war-room">
            <div className="section-title"><div><span className="eyebrow">Central de comando</span><h2>Seu caminho na competição</h2></div></div>
            <div className="war-room-grid">
              <Link to="/ranking"><span>♛</span><div><small>Classificação</small><strong>Ranking oficial</strong><p>Veja pontos por modalidade e sua posição na temporada.</p></div><b>→</b></Link>
              <Link to="/jogador"><span>⚔</span><div><small>Desempenho</small><strong>Ficha do jogador</strong><p>Entenda sua pontuação e acompanhe cada batalha.</p></div><b>→</b></Link>
              <Link to="/auditoria"><span>◈</span><div><small>Transparência</small><strong>Arquivo de batalhas</strong><p>Consulte resultados processados pelo motor Winning Wars.</p></div><b>→</b></Link>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export function RankingPage() {
  const { ranking, loading, error, recarregar } = useRanking();
  const [busca, setBusca] = useState("");
  const filtrado = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    if (!termo) return ranking;
    return ranking.filter((item) => `${item.nome} ${item.tag}`.toLocaleLowerCase("pt-BR").includes(termo));
  }, [busca, ranking]);

  return (
    <div className="page">
      <PageHeader eyebrow="Temporada oficial" title="Ranking de guerreiros" description="Cada estrela, ataque e conquista processada pelo motor Winning Wars forma esta classificação." />
      <div className="toolbar"><label className="search-box"><span>⌕</span><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Buscar jogador ou tag" /></label><span>{filtrado.length} jogadores</span></div>
      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={recarregar} />}
      {!loading && !error && (
        <div className="ranking-table" role="table" aria-label="Ranking oficial">
          <div className="ranking-head" role="row"><span>#</span><span>Jogador</span><span>Guerras</span><span>Raides</span><span>Jogos</span><span>Eventos</span><span>Total</span></div>
          {filtrado.map((player) => (
            <Link className="ranking-row" to={`/jogador/${encodeURIComponent(player.tag)}`} key={player.tag} role="row">
              <span className="rank-number">{player.posicao}</span>
              <span className="player-cell"><PlayerAvatar nome={player.nome} position={player.posicao} /><span><strong>{player.nome}</strong><small>{player.tag}</small></span></span>
              <span data-label="Guerras">{player.guerra}</span><span data-label="Raides">{player.raides}</span><span data-label="Jogos">{player.jogos}</span><span data-label="Eventos">{player.eventos}</span><strong className="total-cell">{player.total}</strong>
            </Link>
          ))}
          {!filtrado.length && <div className="empty-state">Nenhum jogador encontrado para “{busca}”.</div>}
        </div>
      )}
    </div>
  );
}

export function PlayerPage() {
  const { tag } = useParams();
  const navigate = useNavigate();
  const { ranking, loading: rankingLoading } = useRanking();
  const decodedTag = tag ? decodeURIComponent(tag) : "";
  const selected = ranking.find((item) => item.tag === decodedTag) || ranking[0];
  const [audit, setAudit] = useState<PlayerAuditResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    setLoading(true); setError(null); setAudit(null);
    api.jogador(selected.tag).then((result) => active && setAudit(result)).catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "Falha na auditoria.")).finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [selected?.tag]);

  if (rankingLoading) return <div className="page"><Loading /></div>;
  if (!selected) return <div className="page"><ErrorState message="O ranking não possui jogadores." /></div>;

  return (
    <div className="page">
      <PageHeader eyebrow="Jornada do guerreiro" title="Ficha do jogador" description="Pontuação consolidada, modalidades disputadas e justificativa de cada resultado." />
      <label className="player-picker"><span>Selecionar jogador</span><select value={selected.tag} onChange={(event) => navigate(`/jogador/${encodeURIComponent(event.target.value)}`)}>{ranking.map((item) => <option key={item.tag} value={item.tag}>{item.posicao}º · {item.nome} · {item.tag}</option>)}</select></label>
      <section className="player-profile">
        <PlayerAvatar nome={selected.nome} position={selected.posicao} />
        <div><span className="eyebrow">{selected.posicao}º lugar na temporada</span><h2>{selected.nome}</h2><small>{selected.tag}</small></div>
        <strong>{selected.total}<small> pontos</small></strong>
      </section>
      <section className="score-grid">
        <article><span>⚔</span><div><small>Guerras e ligas</small><strong>{selected.guerra}</strong></div></article>
        <article><span>☄</span><div><small>Raides</small><strong>{selected.raides}</strong></div></article>
        <article><span>♟</span><div><small>Jogos do Clã</small><strong>{selected.jogos}</strong></div></article>
        <article><span>◆</span><div><small>Eventos</small><strong>{selected.eventos}</strong></div></article>
      </section>
      <section className="section-block">
        <div className="section-title"><div><span className="eyebrow">Livro de batalha</span><h2>Por que recebeu estes pontos?</h2><p>Cada registro preserva a regra aplicada pelo motor.</p></div>{audit && <span>{audit.total} registros</span>}</div>
        {loading && <Loading label="Buscando o histórico deste jogador…" />}
        {error && <ErrorState message={error} />}
        {audit && <div className="timeline">{audit.registros.map((record) => <AuditRecord key={`${record.tipo}-${record.identificador}`} record={record} />)}</div>}
      </section>
    </div>
  );
}

function AuditRecord({ record }: { record: PlayerAuditResponse["registros"][number] }) {
  const detail = record.jogador;
  const ataques = Array.isArray(detail.ataques) ? detail.ataques : [];
  return (
    <article className="timeline-item">
      <span className={`activity-icon type-${record.tipo}`}>{record.tipo === "guerra" ? "⚔" : "☄"}</span>
      <div className="timeline-body">
        <header><div><span className="type-chip">{rotuloTipo(record.tipo)}</span><strong>{record.adversario ? `vs. ${record.adversario}` : "Fim de semana de raides"}</strong></div><time>{dataAtividade(record.data)}</time></header>
        <p>{detail.motivo?.replaceAll("_", " ") || "Pontuação processada pelo motor."}</p>
        {!!ataques.length && <div className="attack-list">{ataques.map((attack, index) => <span key={`${attack.ordem}-${index}`}><b>{attack.estrelas}★</b> {attack.percentual}% · {attack.alvo_nome || "alvo"} {attack.cv_alvo ? `(CV${attack.cv_alvo})` : ""}</span>)}</div>}
        {typeof detail.capital_resources_looted === "number" && <small>{numero(detail.capital_resources_looted)} de capital saqueado · {typeof detail.ataques === "number" ? detail.ataques : 0} ataques</small>}
      </div>
      <strong className="points-awarded">+{detail.pontos_competicao ?? 0}</strong>
    </article>
  );
}

export function AuditPage() {
  const [activities, setActivities] = useState<AuditActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("todos");
  const load = () => { setLoading(true); setError(null); api.atividades().then((result) => setActivities(result.atividades)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha na auditoria.")).finally(() => setLoading(false)); };
  useEffect(load, []);
  const filtered = filter === "todos" ? activities : activities.filter((item) => item.tipo === filter);

  return (
    <div className="page">
      <PageHeader eyebrow="Arquivo oficial" title="Batalhas encerradas" description="Resultados preservados com origem, participantes e pontuação calculada pelo motor Winning Wars." />
      <div className="filter-tabs" role="tablist">{[["todos", "Todas"], ["guerra", "Guerras"], ["raid", "Raides"], ["liga", "Ligas"]].map(([value, label]) => <button className={filter === value ? "active" : ""} onClick={() => setFilter(value)} key={value}>{label}</button>)}</div>
      {loading && <Loading label="Carregando o arquivo de auditoria…" />}
      {error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && <div className="activity-grid">{filtered.map((activity) => <article className="activity-card" key={`${activity.tipo}-${activity.identificador}`}><header><span className={`activity-icon type-${activity.tipo}`}>{activity.tipo === "guerra" ? "⚔" : activity.tipo === "liga" ? "♛" : "☄"}</span><div><span className="type-chip">{rotuloTipo(activity.tipo)}</span><time>{dataAtividade(activity.data)}</time></div></header><h3>{activity.adversario ? `Winning Wars × ${activity.adversario}` : "Fim de semana de raides"}</h3><div className="activity-stats"><span><small>Jogadores</small><strong>{numero(activity.jogadores)}</strong></span><span><small>Ataques</small><strong>{numero(activity.ataques)}</strong></span><span><small>Pontos</small><strong>{numero(activity.pontos_competicao)}</strong></span></div><small className="activity-id">{activity.identificador}</small></article>)}</div>}
    </div>
  );
}

export function NotFoundPage() {
  return <div className="page"><div className="state-card"><strong>Página não encontrada</strong><Link className="primary-button" to="/">Voltar ao início</Link></div></div>;
}
