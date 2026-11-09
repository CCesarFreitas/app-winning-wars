import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "./api";
import { ErrorState, Loading, PageHeader, PlayerAvatar } from "./components";
import { dataAtividade, numero, rotuloTipo, temporadaLabel } from "./format";
import { useRanking } from "./RankingContext";
import type { AdminParticipationAccount, AdminParticipationResponse, AdminSummary, AuditActivity, LayoutEntry, PlayerAuditResponse, TournamentMatch, TournamentPlayer } from "./types";
import { CREST_URL, townHallUrl } from "./assets";
import { useAdmin } from "./AdminContext";

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
              <Link to="/layouts/guerra"><span>⬢</span><div><small>Defesas</small><strong>Layouts de guerra</strong><p>Bases organizadas por Centro de Vila para copiar no Clash.</p></div><b>→</b></Link>
              <Link to="/layouts/rankeada"><span>⌁</span><div><small>Rankeadas</small><strong>Layouts de rankeada</strong><p>Seleção oficial para proteger troféus e subir no ranking.</p></div><b>→</b></Link>
              <Link to="/torneios"><span>⚡</span><div><small>Arena ao vivo</small><strong>Torneios Winning Wars</strong><p>Chaveamento eliminatório oficial para as lives do clã.</p></div><b>→</b></Link>
              <Link to="/conceitos"><span>✦</span><div><small>Nova identidade</small><strong>Laboratório visual</strong><p>Compare diferentes formas de navegar e acompanhar o ranking ao vivo.</p></div><b>→</b></Link>
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

const CVS = [18, 17, 16, 15, 14, 13, 12, 11, 10, 9];

export function LayoutsPage() {
  const { tipo = "guerra" } = useParams();
  const rankeada = tipo === "rankeada";
  const tipoApi = rankeada ? "Rankeada" : "Guerra";
  const [cv, setCv] = useState(18);
  const [layouts, setLayouts] = useState<LayoutEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = () => {
    setLoading(true); setError(null);
    api.layouts(tipoApi, `CV ${cv}`, 12, 0).then((result) => { setLayouts(result.layouts); setTotal(result.total); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar layouts."))
      .finally(() => setLoading(false));
  };
  const loadMore = () => {
    setLoadingMore(true);
    api.layouts(tipoApi, `CV ${cv}`, 12, layouts.length)
      .then((result) => { setLayouts((current) => [...current, ...result.layouts]); setTotal(result.total); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar mais layouts."))
      .finally(() => setLoadingMore(false));
  };
  useEffect(load, [tipoApi, cv]);
  return <div className="page">
    <PageHeader eyebrow="Arsenal de bases" title={`Layouts oficiais de ${rankeada ? "rankeada" : "guerra"}`} description="Escolha seu Centro de Vila, analise a defesa e abra o layout diretamente no Clash of Clans." />
    <div className="cv-selector" role="tablist" aria-label="Centro de Vila">
      {CVS.map((value) => <button key={value} className={cv === value ? "active" : ""} onClick={() => setCv(value)}><img src={townHallUrl(value)} alt="" /><span>CV {value}</span></button>)}
    </div>
    <section className="layout-heading"><img src={townHallUrl(cv)} alt={`Centro de Vila ${cv}`} /><div><span className="eyebrow">Centro de Vila {cv}</span><h2>Bases de {tipoApi}</h2><p>{total} {total === 1 ? "layout disponível" : "layouts disponíveis"}</p></div></section>
    {loading && <Loading label="Abrindo o arsenal de layouts…" />}
    {error && <ErrorState message={error} onRetry={load} />}
    {!loading && !error && <div className="layout-grid">{layouts.map((layout, index) => <article className="layout-card" key={`${layout.link}-${index}`}>
      <div className="layout-image">{layout.imagem_url ? <img src={layout.imagem_url} alt={`Layout de ${tipoApi} para CV ${cv}`} /> : <img className="layout-placeholder" src={townHallUrl(cv)} alt="" />}</div>
      <div className="layout-card-body"><span>Publicado por {layout.autor || "Winning Wars"}</span>{layout.descricao && <p>{layout.descricao}</p>}<a className="primary-button" href={layout.link} target="_blank" rel="noreferrer">Copiar layout no Clash ↗</a></div>
    </article>)}</div>}
    {!loading && !error && layouts.length < total && <div className="load-more"><button className="secondary-button" onClick={loadMore} disabled={loadingMore}>{loadingMore ? "Carregando…" : `Carregar mais layouts (${layouts.length} de ${total})`}</button></div>}
    {!loading && !error && !layouts.length && <div className="state-card"><strong>Nenhum layout publicado para CV {cv}</strong><span>Escolha outro Centro de Vila ou volte em breve.</span></div>}
  </div>;
}

const REGRAS_TORNEIO = [
  "Respeite participantes, juiz e normas do torneio; comportamento antidesportivo pode causar eliminação.",
  "Os duelos são convocados pelo juiz e os desafios devem usar exatamente o modo de jogo anunciado.",
  "O confronto deve começar em até 30 segundos depois que o desafio for publicado no chat.",
  "Quem não iniciar o ataque no prazo máximo permitido poderá ser eliminado.",
  "Em empate de três estrelas, avança quem concluir o ataque em menor tempo.",
];

function TournamentPlayerCard({ player, winner }: { player: TournamentPlayer | null; winner?: boolean }) {
  if (!player) return <div className="tournament-player bye">Aguardando classificado</div>;
  return <div className={`tournament-player ${winner ? "winner" : ""}`}><img src={townHallUrl(player.cv)} alt={`CV ${player.cv}`} /><span><strong>{player.nome}</strong><small>{player.tag} · CV {player.cv}</small></span></div>;
}

function TournamentMatchCard({ match, index }: { match: TournamentMatch; index: number }) {
  return <article className="tournament-match"><small>Jogo {index + 1}{match.automatico ? " · avanço automático" : ""}</small><TournamentPlayerCard player={match.jogadores[0]} winner={match.vencedor?.tag === match.jogadores[0]?.tag} /><b>VS</b><TournamentPlayerCard player={match.jogadores[1]} winner={match.vencedor?.tag === match.jogadores[1]?.tag} /></article>;
}

export function TournamentPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.torneio>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = () => { setLoading(true); setError(null); api.torneio().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao abrir a arena.")).finally(() => setLoading(false)); };
  useEffect(load, []);
  const torneio = data?.torneio;
  const roster = data?.roster;
  return <div className="page tournament-page">
    <section className="tournament-hero"><div><span className="eyebrow">Arena oficial para lives</span><h1>Torneios Winning Wars</h1><p>Confrontos eliminatórios 1 × 1, da primeira batalha à grande final.</p><div><span>TorneiosWWars · #2CY88CCYU</span><a href="https://www.youtube.com/@winningwarscoc" target="_blank" rel="noreferrer">▶ YouTube @winningwarscoc</a></div></div><img src={CREST_URL} alt="Brasão Winning Wars" /></section>
    <details className="rules-panel" open><summary>Regras oficiais do torneio</summary><ol>{REGRAS_TORNEIO.map((regra, index) => <li key={regra}><b>{String(index + 1).padStart(2, "0")}</b><span>{regra}</span></li>)}</ol></details>
    {loading && <Loading label="Conectando à arena oficial…" />}{error && <ErrorState message={error} onRetry={load} />}
    {!loading && !error && roster && <section className="roster-summary"><div><span className="eyebrow">Elenco em tempo real</span><h2>{roster.clan}</h2><p>{roster.contas.length} contas · {roster.tag}</p></div><div className="roster-cvs">{CVS.map((value) => { const total = roster.contas.filter((p) => p.cv === value).length; return total ? <span key={value}><img src={townHallUrl(value)} alt="" />CV {value}: <b>{total}</b></span> : null; })}</div></section>}
    {!loading && !error && !torneio && <div className="state-card tournament-empty"><strong>A arena está preparada para o próximo torneio</strong><span>O chaveamento aparecerá aqui assim que a organização iniciar a competição.</span></div>}
    {torneio && <><section className="tournament-title"><div><span className="eyebrow">Chaveamento oficial</span><h2>{torneio.nome}</h2><p>{torneio.participantes.length} competidores · CV {torneio.cv} · {torneio.modo}</p></div>{torneio.campeao && <div className="champion-chip">🏆 {torneio.campeao.nome}</div>}</section><div className="bracket">{torneio.rodadas.map((round, roundIndex) => <section className="bracket-round" key={roundIndex}><h3>{torneio.rotulos[roundIndex]}</h3><div>{round.map((match, index) => <TournamentMatchCard key={index} match={match} index={index} />)}</div></section>)}</div></>}
  </div>;
}

type IdentityConcept = "fortaleza_cv" | "fortaleza" | "mapa" | "liga";

const CONCEPTS: Array<{ id: IdentityConcept; title: string; subtitle: string }> = [
  { id: "fortaleza_cv", title: "Fortaleza Real 2.0", subtitle: "Ranking oficial com CV e leitura moderna" },
  { id: "fortaleza", title: "Fortaleza Clássica", subtitle: "Solene, premium e orientada ao campeão" },
  { id: "mapa", title: "Mapa de Guerra", subtitle: "Lúdica, territorial e muito Clash" },
  { id: "liga", title: "Liga Imperial", subtitle: "Esportiva, objetiva e rica em dados" },
];

const CONCEPT_TABS = ["Quartel-general", "Ranking ao vivo", "Planejamento", "Layouts", "Torneios", "Membros", "Admin"];

export function IdentityLabPage() {
  const { ranking, loading, error, recarregar } = useRanking();
  const [concept, setConcept] = useState<IdentityConcept>("fortaleza_cv");
  const leader = ranking[0];
  const active = CONCEPTS.find((item) => item.id === concept)!;
  return <div className="page identity-lab-page">
    <PageHeader eyebrow="Estúdio de identidade" title="Três visões para o Winning Wars" description="Compare navegação, presença dos elementos de Clash of Clans e formas de acompanhar a competição em tempo real." />
    <div className="concept-switcher" role="tablist" aria-label="Conceitos visuais">
      {CONCEPTS.map((item, index) => <button key={item.id} className={concept === item.id ? "active" : ""} onClick={() => setConcept(item.id)}><b>0{index + 1}</b><span><strong>{item.title}</strong><small>{item.subtitle}</small></span></button>)}
    </div>
    {loading && <Loading label="Carregando o ranking para as propostas…" />}
    {error && <ErrorState message={error} onRetry={recarregar} />}
    {!loading && !error && <section className={`concept-stage concept-${concept}`}>
      <header className="concept-brandbar"><div><img src={CREST_URL} alt="Brasão Winning Wars" /><span><small>Clash · Compete · Conquer</small><strong>Winning Wars</strong></span></div><span className="concept-live"><i className="live-dot" /> Ranking em tempo real</span></header>
      <nav className="concept-tabs" aria-label="Prévia das abas principais">{CONCEPT_TABS.map((tab, index) => <button className={index === 1 ? "active" : ""} key={tab}><span>{["⌂","♛","⚔","⬢","⚡","♟","◆"][index]}</span>{tab}</button>)}</nav>
      <div className="concept-intro"><div><span className="eyebrow">{active.title}</span><h2>{concept === "mapa" ? "O mapa da conquista" : concept === "liga" ? "A corrida pelo topo" : concept === "fortaleza_cv" ? "Ranking oficial da temporada" : "O salão dos campeões"}</h2><p>{active.subtitle}. Dados oficiais processados pelo motor Winning Wars.</p></div>{leader && <div className="concept-leader"><RankingTownHall player={leader} compact /><span><small>Líder atual</small><strong>{leader.nome}</strong><b>{leader.total} pts</b></span></div>}</div>
      {concept === "fortaleza_cv" && <FortressCvRanking ranking={ranking.slice(0, 12)} />}
      {concept === "fortaleza" && <FortressRanking ranking={ranking.slice(0, 8)} />}
      {concept === "mapa" && <WarMapRanking ranking={ranking.slice(0, 8)} />}
      {concept === "liga" && <LeagueRanking ranking={ranking.slice(0, 10)} />}
      <footer className="concept-foot"><span>Atualização única compartilhada entre todas as visões</span><b>Zero consulta adicional à Oracle</b></footer>
    </section>}
  </div>;
}

function RankingTownHall({ player, compact = false }: { player: ReturnType<typeof useRanking>["ranking"][number]; compact?: boolean }) {
  const cvValido = typeof player.cv === "number" && player.cv >= 9 && player.cv <= 18;
  return <span className={`ranking-th ${compact ? "compact" : ""} ${cvValido ? "" : "unknown"}`}>
    {cvValido ? <img src={townHallUrl(player.cv!)} alt={`Centro de Vila ${player.cv}`} /> : <span>?</span>}
    <small>{cvValido ? `CV ${player.cv}` : "CV —"}</small>
  </span>;
}

function FortressCvRanking({ ranking }: { ranking: ReturnType<typeof useRanking>["ranking"] }) {
  const max = Math.max(1, ...ranking.map((item) => item.total));
  return <div className="fortress-cv-ranking">
    <div className="fortress-prize"><span>🎟️</span><div><small>Competição Winning Wars</small><strong>Top 3 garantem o Passe Dourado</strong></div><b>Temporada em disputa</b></div>
    <div className="fortress-cv-podium">{ranking.slice(0, 3).map((player) => <article key={player.tag} className={`cv-podium-card place-${player.posicao}`}>
      <span className="cv-place">{player.posicao === 1 ? "🥇" : player.posicao === 2 ? "🥈" : "🥉"} {player.posicao}º lugar</span>
      <RankingTownHall player={player} />
      <div><strong>{player.nome}</strong><small>{player.tag}</small><span>⚔ {player.guerra} · ☄ {player.raides} · ♟ {player.jogos} · ◆ {player.eventos}</span></div>
      <b>{player.total}<small> pontos</small></b>
    </article>)}</div>
    <div className="fortress-cv-list"><header><span>Pos.</span><span>Vila e jogador</span><span>Desempenho da temporada</span><span>Total</span></header>{ranking.slice(3).map((player) => <article key={player.tag}>
      <span className="cv-list-position">{player.posicao}</span>
      <span className="cv-list-player"><RankingTownHall player={player} compact /><span><strong>{player.nome}</strong><small>{player.tag}</small></span></span>
      <span className="cv-list-progress"><i style={{ width: `${Math.max(8, player.total / max * 100)}%` }} /><small>⚔ {player.guerra} guerras · ☄ {player.raides} raides · ♟ {player.jogos} jogos · ◆ {player.eventos} eventos</small></span>
      <b>{player.total}<small> pts</small></b>
    </article>)}</div>
  </div>;
}

function FortressRanking({ ranking }: { ranking: ReturnType<typeof useRanking>["ranking"] }) {
  return <div className="fortress-ranking"><div className="fortress-podium">{ranking.slice(0, 3).map((player) => <article key={player.tag} className={`fortress-place place-${player.posicao}`}><span>{player.posicao}º</span><PlayerAvatar nome={player.nome} position={player.posicao} /><strong>{player.nome}</strong><small>{player.tag}</small><b>{player.total} pontos</b></article>)}</div><div className="fortress-list">{ranking.slice(3).map((player) => <div key={player.tag}><span>{player.posicao}</span><PlayerAvatar nome={player.nome} /><strong>{player.nome}</strong><small>⚔ {player.guerra} · ☄ {player.raides} · ♟ {player.jogos}</small><b>{player.total}</b></div>)}</div></div>;
}

function WarMapRanking({ ranking }: { ranking: ReturnType<typeof useRanking>["ranking"] }) {
  const max = Math.max(1, ...ranking.map((item) => item.total));
  return <div className="war-map-ranking"><div className="map-path" />{ranking.map((player, index) => <article key={player.tag} style={{ "--progress": `${Math.max(12, (player.total / max) * 100)}%` } as CSSProperties}><div className="map-rank">{player.posicao}</div><div className="map-player"><strong>{player.nome}</strong><small>{player.tag}</small></div><div className="map-bar"><i /><span>{index === 0 ? "Fortaleza do líder" : `${player.total} pontos conquistados`}</span></div><img src={townHallUrl(18 - (index % 5))} alt="" /><b>{player.total}</b></article>)}</div>;
}

function LeagueRanking({ ranking }: { ranking: ReturnType<typeof useRanking>["ranking"] }) {
  return <div className="league-ranking"><header><span>Pos.</span><span>Guerreiro</span><span>Guerras</span><span>Raides</span><span>Jogos</span><span>Total</span></header>{ranking.map((player) => <article key={player.tag}><span className="league-position">{player.posicao}</span><span className="league-player"><PlayerAvatar nome={player.nome} position={player.posicao} /><span><strong>{player.nome}</strong><small>{player.tag}</small></span></span><span data-label="Guerras">{player.guerra}</span><span data-label="Raides">{player.raides}</span><span data-label="Jogos">{player.jogos}</span><b>{player.total}</b></article>)}</div>;
}

export function AdminLoginPage() {
  const navigate = useNavigate();
  const { session, loading, refresh } = useAdmin();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const ambienteSeguro = window.isSecureContext;

  useEffect(() => {
    if (!loading && session.autenticado) navigate("/admin", { replace: true });
  }, [loading, navigate, session.autenticado]);

  const entrar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ambienteSeguro) return;
    setEnviando(true); setErro(null);
    try {
      await api.adminLogin(usuario.trim(), senha);
      setSenha("");
      await refresh();
      navigate("/admin", { replace: true });
    } catch (reason) {
      setErro(reason instanceof Error ? reason.message : "Não foi possível entrar.");
    } finally {
      setEnviando(false);
    }
  };

  return <div className="page admin-page">
    <PageHeader eyebrow="Acesso restrito" title="Central administrativa" description="Operações protegidas, auditáveis e executadas pela API privada da Oracle." />
    <div className="admin-login-layout">
      <section className="admin-login-card">
        <div className="admin-lock" aria-hidden="true">◆</div>
        <div><span className="eyebrow">Identificação da liderança</span><h2>Entrar como administrador</h2><p>A sessão fica protegida no navegador e sua senha nunca é armazenada no site.</p></div>
        {!ambienteSeguro && <div className="security-warning"><strong>HTTPS necessário</strong><span>O login foi bloqueado neste endereço HTTP para impedir a transmissão insegura da senha. A interface está pronta para ser ativada depois da configuração do domínio e certificado.</span></div>}
        <form onSubmit={entrar}>
          <label><span>Usuário</span><input autoComplete="username" value={usuario} onChange={(event) => setUsuario(event.target.value)} disabled={!ambienteSeguro || enviando} /></label>
          <label><span>Senha</span><input type="password" autoComplete="current-password" value={senha} onChange={(event) => setSenha(event.target.value)} disabled={!ambienteSeguro || enviando} /></label>
          {erro && <div className="form-error" role="alert">{erro}</div>}
          <button className="primary-button" type="submit" disabled={!ambienteSeguro || enviando || !usuario.trim() || !senha}>{enviando ? "Validando…" : "Entrar no painel"}</button>
        </form>
      </section>
      <aside className="admin-security-card"><span>Proteções previstas</span><ul><li>Cookie de sessão inacessível ao JavaScript</li><li>Validação do administrador a cada operação</li><li>Limite de tentativas de login</li><li>Credenciais do Google apenas na Oracle</li><li>Primeira etapa estritamente somente leitura</li></ul></aside>
    </div>
  </div>;
}

export function AdminPage() {
  const navigate = useNavigate();
  const { session, loading: sessionLoading, refresh } = useAdmin();
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionLoading || !session.autenticado) return;
    setLoading(true); setError(null);
    api.adminSummary().then(setSummary).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar o painel.")).finally(() => setLoading(false));
  }, [session.autenticado, sessionLoading]);

  const sair = async () => {
    await api.adminLogout();
    await refresh();
    navigate("/", { replace: true });
  };

  if (sessionLoading) return <div className="page"><Loading label="Conferindo sessão administrativa…" /></div>;
  if (!session.autenticado) return <div className="page admin-page"><PageHeader eyebrow="Central administrativa" title="Sessão protegida" description="Entre com uma conta autorizada para acessar os controles." /><div className="state-card"><strong>Acesso administrativo necessário</strong><span>Nenhum dado protegido foi carregado.</span><Link className="primary-button" to="/admin/login">Entrar como administrador</Link></div></div>;

  return <div className="page admin-page">
    <div className="admin-heading"><PageHeader eyebrow="Central de comando" title={`Olá, ${session.usuario}`} description="Visão protegida do estado atual da competição." /><button className="secondary-button" onClick={sair}>Encerrar sessão</button></div>
    <div className="read-only-banner"><span>◉</span><div><strong>Homologação somente leitura</strong><small>Nenhuma alteração na planilha pode ser feita por esta versão.</small></div></div>
    {loading && <Loading label="Carregando controles administrativos…" />}
    {error && <ErrorState message={error} />}
    {summary && <>
      <section className="admin-metrics">
        <article><small>Temporada</small><strong>{summary.temporada_nome || summary.temporada}</strong><span>{summary.ranking.jogadores} contas no ranking</span></article>
        <article><small>Participação</small><strong>{summary.participacao.habilitadas}</strong><span>contas habilitadas</span></article>
        <article><small>Bloqueios</small><strong>{summary.participacao.bloqueadas}</strong><span>decisões administrativas</span></article>
        <article><small>Nível de acesso</small><strong>{summary.admin.nivel}</strong><span>{summary.admin.usuario}</span></article>
      </section>
      <section className="admin-modules"><div className="section-title"><div><span className="eyebrow">Próximas migrações</span><h2>Controles administrativos</h2><p>Cada módulo será liberado somente depois da validação em paralelo com o app oficial.</p></div></div><div>
        {["Participação e vínculos", "Jogos do Clã e eventos", "Revisões de pontuação", "Layouts e torneios", "Comunicação e agenda", "Fechamento mensal"].map((label, index) => <article key={label}><span>{String(index + 1).padStart(2, "0")}</span><strong>{index === 0 ? <Link to="/admin/participacao">{label}</Link> : label}</strong><small>{index === 0 ? "Disponível para consulta" : "Aguardando migração"}</small></article>)}
      </div></section>
    </>}
  </div>;
}

const PARTICIPATION_STATUS: Record<AdminParticipationAccount["situacao"], string> = {
  MEMBRO_ATUAL: "No clã",
  AUSENTE_AGORA: "Ausente agora",
  RETORNOU_AO_CLA: "Retornou ao clã",
  ENTROU_APOS_INICIO_DO_HISTORICO: "Entrada recente",
  SEM_REGISTRO_NO_CLA: "Sem registro no clã",
};

export function AdminParticipationPage() {
  const { session, loading: sessionLoading } = useAdmin();
  const [data, setData] = useState<AdminParticipationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("todas");

  useEffect(() => {
    if (sessionLoading || !session.autenticado) return;
    setLoading(true); setError(null);
    api.adminParticipation().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar participação.")).finally(() => setLoading(false));
  }, [session.autenticado, sessionLoading]);

  const accounts = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("pt-BR");
    return (data?.contas || []).filter((account) => {
      const matchesTerm = !term || `${account.nome} ${account.tag} ${account.participante_id || ""}`.toLocaleLowerCase("pt-BR").includes(term);
      const matchesFilter = filter === "todas"
        || (filter === "no_cla" && account.no_cla)
        || (filter === "ausentes" && !account.no_cla)
        || (filter === "habilitadas" && account.habilitada === "TRUE")
        || (filter === "bloqueadas" && account.habilitada === "FALSE")
        || (filter === "sem_decisao" && !account.habilitada);
      return matchesTerm && matchesFilter;
    });
  }, [data, filter, search]);

  if (sessionLoading) return <div className="page"><Loading label="Conferindo sessão administrativa…" /></div>;
  if (!session.autenticado) return <div className="page admin-page"><PageHeader eyebrow="Participação e vínculos" title="Acesso protegido" description="Esta relação contém decisões administrativas e exige autenticação." /><div className="state-card"><strong>Sessão administrativa necessária</strong><Link className="primary-button" to="/admin/login">Entrar como administrador</Link></div></div>;

  return <div className="page admin-page participation-page">
    <div className="admin-subnav"><Link to="/admin">← Voltar ao painel</Link><span>Somente leitura</span></div>
    <PageHeader eyebrow="Controle da competição" title="Participação e vínculos" description="Presença no clã é um alerta operacional. Somente uma decisão administrativa pode bloquear uma conta." />
    {loading && <Loading label="Conferindo contas, vínculos e presença…" />}
    {error && <ErrorState message={error} />}
    {data && <>
      <section className="participation-stats">
        <article><small>Contas monitoradas</small><strong>{data.contagens.total}</strong></article>
        <article><small>No clã agora</small><strong>{data.contagens.no_cla}</strong></article>
        <article><small>Fora do clã</small><strong>{data.contagens.ausentes}</strong></article>
        <article className="success"><small>Habilitadas</small><strong>{data.contagens.habilitadas}</strong></article>
        <article className="danger"><small>Bloqueadas</small><strong>{data.contagens.bloqueadas}</strong></article>
        <article><small>Sem decisão</small><strong>{data.contagens.sem_decisao}</strong></article>
      </section>
      <div className="participation-note"><strong>Critério oficial</strong><span>{data.criterio}</span></div>
      <div className="participation-toolbar"><label className="search-box"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar nome, tag ou ID" /></label><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="todas">Todas as contas</option><option value="no_cla">No clã</option><option value="ausentes">Fora do clã</option><option value="habilitadas">Habilitadas</option><option value="bloqueadas">Bloqueadas</option><option value="sem_decisao">Sem decisão</option></select><span>{accounts.length} resultados</span></div>
      <section className="participation-list"><header><span>Conta</span><span>Presença</span><span>Competição</span><span>Última decisão</span><span>Pontos</span></header>{accounts.map((account) => <article key={account.tag}>
        <div className="participation-player">{account.cv ? <img src={townHallUrl(account.cv)} alt={`CV ${account.cv}`} /> : <span>?</span>}<div><strong>{account.nome}</strong><small>{account.tag} · ID {account.participante_id || "—"}{account.cv ? ` · CV ${account.cv}` : ""}</small></div></div>
        <div><span className={`status-chip ${account.no_cla ? "online" : "away"}`}>{PARTICIPATION_STATUS[account.situacao]}</span><small>{account.ultima_vista ? `Última presença: ${dataAtividade(account.ultima_vista)}` : "Sem histórico de presença"}</small></div>
        <div><span className={`status-chip ${account.habilitada === "FALSE" ? "blocked" : account.habilitada === "TRUE" ? "enabled" : "neutral"}`}>{account.habilitada === "FALSE" ? "Bloqueada" : account.habilitada === "TRUE" ? "Habilitada" : "Sem decisão"}</span><small>{account.inscrita ? "Inscrita na temporada" : "Ainda não inscrita"}</small></div>
        <div className="decision-cell"><strong>{account.administrador || (account.origem_decisao === "CADASTRO" ? "Automática" : "—")}</strong><small>{account.motivo || "Nenhuma decisão administrativa"}</small></div>
        <b>{account.pontos}<small> pts</small></b>
      </article>)}</section>
      {!accounts.length && <div className="state-card"><strong>Nenhuma conta encontrada</strong><span>Altere a busca ou o filtro selecionado.</span></div>}
    </>}
  </div>;
}

export function NotFoundPage() {
  return <div className="page"><div className="state-card"><strong>Página não encontrada</strong><Link className="primary-button" to="/">Voltar ao início</Link></div></div>;
}
