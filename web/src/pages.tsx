import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, LayoutsDuplicadosError } from "./api";
import { ErrorState, Loading, PageHeader, PlayerAvatar } from "./components";
import { dataAtividade, numero, rotuloTipo, temporadaLabel } from "./format";
import { useRanking } from "./RankingContext";
import type { AdminLayoutDuplicate, AdminManualProposal, AdminManualResponse, AdminParticipationAccount, AdminParticipationResponse, AdminSummary, AuditActivity, ClanResponse, LayoutEntry, PlanningClan, PlanningEnvelope, PlanningMember, PlayerAuditResponse, RankingDetailsResponse, TournamentMatch, TournamentPlayer } from "./types";
import { CREST_URL, townHallUrl } from "./assets";
import { useAdmin } from "./AdminContext";
import { exportCompactRanking, exportDetailedRanking } from "./rankingExport";

export function HomePage() {
  const { ranking, loading, error, recarregar } = useRanking();
  const { session } = useAdmin();
  const lider = ranking[0];
  const pontos = ranking.reduce((total, player) => total + player.total, 0);
  const temporada = temporadaLabel(lider?.temporada);
  const [clan, setClan] = useState<ClanResponse | null>(null);
  useEffect(() => { api.clan().then(setClan).catch(() => undefined); }, []);

  return (
    <div className="page home-page">
      <section className="hero">
        <div className="hero-copy">
          <span className="battle-status"><i className="live-dot" /> Temporada em disputa · {temporada}</span>
          <h1>Seu centro de comando<br /><em>no Winning Wars.</em></h1>
          <p>Acompanhe a competição dos passes em tempo real, consulte o desempenho individual dos membros e encontre layouts de guerra e rankeada, informações sobre eventos e torneios da comunidade Winning Wars.</p>
          <div className="hero-actions">
            <Link className="primary-button" to="/ranking"><span>♛</span> Entrar no ranking</Link>
            <Link className="secondary-button" to={session.autenticado ? "/auditoria" : "/regras"}>{session.autenticado ? "Ver batalhas encerradas" : "Conhecer as regras"} <span>→</span></Link>
          </div>
        </div>
        <div className="hero-emblem" aria-hidden="true">
          <span className="emblem-glow" />
          <img src={CREST_URL} alt="" />
          <div className="clan-level"><small>Nível do clã</small><strong>{clan?.nivel ?? "—"}</strong></div>
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
                <Link to={session.autenticado ? `/jogador/${encodeURIComponent(player.tag)}` : "/ranking"} className={`podium-card place-${player.posicao}`} key={player.tag}>
                  <span className="place-badge">{player.posicao}º</span>
                  <RankingTownHall player={player} compact />
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
              {session.autenticado && <Link to="/jogador"><span>⚔</span><div><small>Administração</small><strong>Ficha do jogador</strong><p>Confira a origem da pontuação e cada batalha processada.</p></div><b>→</b></Link>}
              {session.autenticado && <Link to="/auditoria"><span>◈</span><div><small>Administração</small><strong>Arquivo de batalhas</strong><p>Consulte os registros detalhados preservados pelo motor.</p></div><b>→</b></Link>}
              <Link to="/planejamento"><span>⌖</span><div><small>Estratégia</small><strong>Planejador de guerras</strong><p>Compare os Centros de Vila inscritos e o desempenho observado dos adversários.</p></div><b>→</b></Link>
              <Link to="/layouts/guerra"><span>⬢</span><div><small>Defesas</small><strong>Layouts de guerra</strong><p>Bases organizadas por Centro de Vila para copiar no Clash.</p></div><b>→</b></Link>
              <Link to="/layouts/rankeada"><span>⌁</span><div><small>Rankeadas</small><strong>Layouts Rankeada</strong><p>Seleção oficial para proteger troféus e subir no ranking.</p></div><b>→</b></Link>
              <Link to="/torneios"><span>⚡</span><div><small>Arena ao vivo</small><strong>Torneios Winning Wars</strong><p>Chaveamento eliminatório oficial para as lives do clã.</p></div><b>→</b></Link>
              <Link to="/regras"><span>▤</span><div><small>Regras oficiais</small><strong>Clã e competição dos passes</strong><p>Consulte os critérios de convivência, participação e premiação.</p></div><b>→</b></Link>
            </div>
          </section>
          <section className="community-gates">
            <div className="section-title"><div><span className="eyebrow">Portões da comunidade</span><h2>Entre no clã e conecte sua vila</h2><p>Acessos oficiais para jogar, acompanhar os avisos e participar das atividades.</p></div></div>
            <div className="community-gates-grid">
              <a className="community-gate supercell-gate" href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63" target="_blank" rel="noreferrer"><span className="scid-mark">ID</span><div><small>Conta oficial</small><strong>Adicionar ao Supercell ID</strong><p>Abra o Clash of Clans e adicione o perfil Winning Wars.</p></div><b>↗</b></a>
              <a className="community-gate whatsapp-gate" href="https://chat.whatsapp.com/FKFc5y323PCBnTFdsjhv64" target="_blank" rel="noreferrer"><img src="/assets/whatsapp.svg" alt="WhatsApp" /><div><small>Comunidade</small><strong>Entrar no grupo do clã</strong><p>Receba convocações, avisos e informações das atividades.</p></div><b>↗</b></a>
              <a className="community-gate vastaya-gate" href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y" target="_blank" rel="noreferrer"><img src={CREST_URL} alt="Brasão Winning Wars" /><div><small>Clã secundário</small><strong>Clã Secundário Vastaya</strong><p>Abra o perfil do nosso clã secundário diretamente no Clash.</p></div><b>↗</b></a>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export function RankingPage() {
  const { ranking, loading, error, recarregar } = useRanking();
  const { session } = useAdmin();
  const [busca, setBusca] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const filtrado = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase("pt-BR");
    if (!termo) return ranking;
    return ranking.filter((item) => `${item.nome} ${item.tag}`.toLocaleLowerCase("pt-BR").includes(termo));
  }, [busca, ranking]);

  return (
    <div className="page">
      <PageHeader eyebrow="Fortaleza Real" title="Ranking oficial da temporada" description="A classificação atual do Winning Wars, com Centro de Vila, desempenho por modalidade e pontuação validada pelo motor." />
      <div className="toolbar"><label className="search-box"><span>⌕</span><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Buscar jogador ou tag" /></label><span>{filtrado.length} jogadores · <Link to="/ranking/detalhado">ver pontos por atividade →</Link></span></div>
      {session.autenticado && <div className="ranking-export-bar"><div><strong>Exportação administrativa</strong><span>A imagem compacta incluirá os jogadores visíveis neste filtro.</span></div><button type="button" disabled={exporting || !filtrado.length} onClick={async () => { setExporting(true); setExportError(""); try { await exportCompactRanking(filtrado); } catch (reason) { setExportError(reason instanceof Error ? reason.message : "Falha ao gerar a imagem."); } finally { setExporting(false); } }}>{exporting ? "Gerando PNG…" : "📸 Baixar tabela compacta · PNG HD"}</button></div>}
      {exportError && <div className="state-card error-state"><strong>Não foi possível gerar a imagem</strong><span>{exportError}</span></div>}
      {loading && <Loading />}
      {error && <ErrorState message={error} onRetry={recarregar} />}
      {!loading && !error && !!filtrado.length && <FortressCvRanking ranking={filtrado} />}
      {!loading && !error && !filtrado.length && <div className="empty-state">Nenhum jogador encontrado para “{busca}”.</div>}
    </div>
  );
}

export function DetailedRankingPage() {
  const { session } = useAdmin();
  const [data, setData] = useState<RankingDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [type, setType] = useState("todos");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  const load = () => {
    setLoading(true); setError(null);
    api.rankingDetails().then(setData)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar a tabela detalhada."))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const columns = useMemo(() => data?.colunas.filter((column) => type === "todos" || column.tipo === type) ?? [], [data, type]);
  const players = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("pt-BR");
    if (!term) return data?.jogadores ?? [];
    return (data?.jogadores ?? []).filter((player) => `${player.nome} ${player.tag}`.toLocaleLowerCase("pt-BR").includes(term));
  }, [data, search]);

  return <div className="page">
    <PageHeader eyebrow="Livro da temporada" title="Tabela detalhada" description="Confira quanto cada jogador recebeu em cada guerra, Liga, raide, Jogos do Clã e evento." />
    <div className="detail-controls">
      <label className="search-box"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar jogador ou tag" /></label>
      <div className="filter-tabs" role="tablist" aria-label="Filtrar modalidade">
        {[['todos', 'Todas'], ['guerra', 'Guerras'], ['liga', 'Liga'], ['raide', 'Raides'], ['jogos', 'Jogos'], ['eventos', 'Eventos']].map(([value, label]) => <button className={type === value ? "active" : ""} onClick={() => setType(value)} key={value}>{label}</button>)}
      </div>
    </div>
    {loading && <Loading label="Montando a tabela oficial…" />}
    {error && <ErrorState message={error} onRetry={load} />}
    {data && !loading && !error && <>
      <div className="detail-summary"><span><strong>{players.length}</strong> jogadores</span><span><strong>{columns.length}</strong> atividades exibidas</span><small>Atualizado em {dataAtividade(data.atualizado_em)}</small></div>
      {session.autenticado && <div className="ranking-export-bar detailed"><div><strong>Exportação administrativa</strong><span>O PNG respeitará a busca e as modalidades selecionadas acima.</span></div><button type="button" disabled={exporting || !players.length} onClick={async () => { setExporting(true); setExportError(""); try { await exportDetailedRanking(data, columns, players); } catch (reason) { setExportError(reason instanceof Error ? reason.message : "Falha ao gerar a imagem."); } finally { setExporting(false); } }}>{exporting ? "Montando tabela em alta resolução…" : "🖼️ Baixar tabela detalhada · PNG HD"}</button></div>}
      {exportError && <div className="state-card error-state"><strong>Não foi possível gerar a imagem</strong><span>{exportError}</span></div>}
      <div className="detail-table" style={{ "--activity-count": Math.max(columns.length, 1) } as CSSProperties}>
        <div className="detail-head"><span>#</span><span>Jogador</span>{columns.map((column) => <span className={`kind-${column.tipo}`} key={column.chave}>{column.rotulo}</span>)}<span>Total</span></div>
        {players.map((player) => <article className="detail-row" key={player.tag}>
          <span className="rank-number">{player.posicao}</span>
          <Link className="detail-player" to={`/jogador/${encodeURIComponent(player.tag)}`}><RankingTownHall player={player} compact /><span><strong>{player.nome}</strong><small>{player.tag}</small></span></Link>
          <div className="detail-scores">{columns.map((column) => <span className={`kind-${column.tipo}`} key={column.chave}><small>{column.rotulo}</small><strong>{player.pontos[column.chave] ?? 0}</strong></span>)}</div>
          <strong className="detail-total"><small>Total</small>{player.total}</strong>
        </article>)}
        {!players.length && <div className="empty-state">Nenhum jogador encontrado.</div>}
      </div>
    </>}
  </div>;
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
      <section className="player-profile fortress-player-profile">
        <RankingTownHall player={selected} />
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
  const { session } = useAdmin();
  const rankeada = tipo === "rankeada";
  const tipoApi = rankeada ? "Rankeada" : "Guerra";
  const [cv, setCv] = useState(18);
  const [layouts, setLayouts] = useState<LayoutEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState("");
  const [deletingLink, setDeletingLink] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteNotice, setDeleteNotice] = useState("");
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
  const deleteLayout = async (layout: LayoutEntry) => {
    setDeletingLink(layout.link); setDeleteError(null); setDeleteNotice("");
    try {
      const result = await api.adminLayoutDelete(tipoApi as "Guerra" | "Rankeada", cv, layout.link);
      setConfirmDelete("");
      setDeleteNotice(`${result.removidos} registro(s) removido(s) e conferido(s).`);
      load();
    } catch (reason) {
      setDeleteError(reason instanceof Error ? reason.message : "Não foi possível excluir o layout.");
    } finally { setDeletingLink(""); }
  };
  useEffect(load, [tipoApi, cv]);
  return <div className="page">
    <PageHeader eyebrow="Arsenal de bases" title={rankeada ? "Layouts Rankeada" : "Layouts oficiais de guerra"} description="Escolha seu Centro de Vila, analise a defesa e abra o layout diretamente no Clash of Clans." />
    <div className="cv-selector" role="tablist" aria-label="Centro de Vila">
      {CVS.map((value) => <button key={value} className={cv === value ? "active" : ""} onClick={() => setCv(value)}><img src={townHallUrl(value)} alt="" /><span>CV {value}</span></button>)}
    </div>
    <section className="layout-heading"><img src={townHallUrl(cv)} alt={`Centro de Vila ${cv}`} /><div><span className="eyebrow">Centro de Vila {cv}</span><h2>Bases de {tipoApi}</h2><p>{total} {total === 1 ? "layout disponível" : "layouts disponíveis"}</p></div></section>
    {session.autenticado && <LayoutPublisher tipo={tipoApi as "Guerra" | "Rankeada"} cv={cv} onPublished={load} />}
    {deleteError && <div className="state-card error-state"><strong>Não foi possível excluir o layout</strong><span>{deleteError}</span></div>}
    {deleteNotice && <div className="admin-success">✓ {deleteNotice} A imagem externa foi preservada.</div>}
    {loading && <Loading label="Abrindo o arsenal de layouts…" />}
    {error && <ErrorState message={error} onRetry={load} />}
    {!loading && !error && <div className="layout-grid">{layouts.map((layout, index) => <article className="layout-card" key={`${layout.link}-${index}`}>
      <div className="layout-image">{layout.imagem_url ? <img src={layout.imagem_url} alt={`Layout de ${tipoApi} para CV ${cv}`} /> : <img className="layout-placeholder" src={townHallUrl(cv)} alt="" />}</div>
      <div className="layout-card-body"><span>Publicado por {layout.autor || "Winning Wars"}</span>{layout.descricao && <p>{layout.descricao}</p>}<a className="primary-button" href={layout.link} target="_blank" rel="noreferrer">Copiar layout no Clash ↗</a>{session.autenticado && <div className="layout-admin-delete">{confirmDelete !== layout.link ? <button type="button" onClick={() => { setConfirmDelete(layout.link); setDeleteError(null); setDeleteNotice(""); }}>🗑 Excluir layout</button> : <div role="alertdialog" aria-label="Confirmar exclusão do layout"><strong>Excluir este layout?</strong><span>Ele será removido da galeria e da planilha. A imagem externa será preservada.</span><div><button type="button" onClick={() => setConfirmDelete("")} disabled={deletingLink === layout.link}>Cancelar</button><button className="danger" type="button" onClick={() => deleteLayout(layout)} disabled={deletingLink === layout.link}>{deletingLink === layout.link ? "Excluindo…" : "Confirmar exclusão"}</button></div></div>}</div>}</div>
    </article>)}</div>}
    {!loading && !error && layouts.length < total && <div className="load-more"><button className="secondary-button" onClick={loadMore} disabled={loadingMore}>{loadingMore ? "Carregando…" : `Carregar mais layouts (${layouts.length} de ${total})`}</button></div>}
    {!loading && !error && !layouts.length && <div className="state-card"><strong>Nenhum layout publicado para CV {cv}</strong><span>Escolha outro Centro de Vila ou volte em breve.</span></div>}
  </div>;
}

const MAIN_CLAN_TAG = "#YVLGUJQY";

function memberCv(member: PlanningMember) {
  return Number(member.townHallLevel ?? member.townhallLevel ?? 0);
}

function cvDistribution(members: PlanningMember[]) {
  const counts = new Map<number, number>();
  members.forEach((member) => { const cv = memberCv(member); if (cv > 0) counts.set(cv, (counts.get(cv) || 0) + 1); });
  return [...counts.entries()].sort((a, b) => b[0] - a[0]);
}

function CvBars({ members, label }: { members: PlanningMember[]; label: string }) {
  const distribution = cvDistribution(members);
  const maximum = Math.max(...distribution.map(([, count]) => count), 1);
  return <div className="planning-cv-bars"><small>{label} · {members.length} vilas</small>{distribution.map(([cv, count]) => <div key={cv}><img src={townHallUrl(cv)} alt={`CV ${cv}`} /><span>CV {cv}</span><i><b style={{ width: `${Math.max(10, (count / maximum) * 100)}%` }} /></i><strong>{count}</strong></div>)}</div>;
}

function sideForClan(war: PlanningEnvelope, tag: string): PlanningClan | null {
  if (war.dados.clan.tag === tag) return war.dados.clan;
  if (war.dados.opponent.tag === tag) return war.dados.opponent;
  return null;
}

export function PlanningPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.planning>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opponentTag, setOpponentTag] = useState("");
  const load = () => { setLoading(true); setError(null); api.planning().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar o planejamento.")).finally(() => setLoading(false)); };
  useEffect(load, []);
  const clans = data?.grupo?.dados.clans || [];
  const opponents = clans.filter((clan) => clan.tag !== MAIN_CLAN_TAG);
  const chosenTag = opponentTag || opponents[0]?.tag || "";
  const chosen = opponents.find((clan) => clan.tag === chosenTag) || null;
  const leagueWars = data?.guerras_liga || [];
  const observedWars = chosen ? leagueWars.filter((war) => !!sideForClan(war, chosen.tag)) : [];
  const observedAttacks = observedWars.flatMap((war) => sideForClan(war, chosenTag)?.members.flatMap((member) => member.attacks || []) || []);
  const triples = observedAttacks.filter((attack) => attack.stars === 3).length;
  const avgDestruction = observedAttacks.length ? observedAttacks.reduce((sum, attack) => sum + attack.destructionPercentage, 0) / observedAttacks.length : 0;
  const durations = observedAttacks.map((attack) => attack.duration).filter((duration): duration is number => typeof duration === "number");
  const avgDuration = durations.length ? durations.reduce((sum, duration) => sum + duration, 0) / durations.length : 0;
  const latestWar = [...leagueWars].reverse().find((war) => !!sideForClan(war, MAIN_CLAN_TAG)) || null;
  const wwSide = latestWar ? sideForClan(latestWar, MAIN_CLAN_TAG) : null;
  const currentOpponent = latestWar ? (latestWar.dados.clan.tag === MAIN_CLAN_TAG ? latestWar.dados.opponent : latestWar.dados.clan) : null;

  return <div className="page planning-page">
    <PageHeader eyebrow="Sala de estratégia" title="Planejador de guerras e Liga" description="Compare as vilas inscritas e escaladas, analise o histórico observado dos adversários e prepare a melhor escalação e defesa." />
    {loading && <Loading label="Montando o mapa estratégico…" />}
    {error && <ErrorState message={error} onRetry={load} />}
    {data && !loading && !error && <>
      <section className="planning-status"><div><span className="live-dot" /><strong>{data.grupo ? `Liga ${data.grupo.dados.season}` : "Sem Liga ativa"}</strong><small>Atualizado em {dataAtividade(data.publicado_em)}</small></div><span>{data.pendencias.length ? `${data.pendencias.length} consultas pendentes` : "Dados conferidos"}</span></section>
      {latestWar && wwSide && currentOpponent && <section className="planning-current"><div><span className="eyebrow">Escalação mais recente · rodada {latestWar.rodada}</span><h2>Winning Wars × {currentOpponent.name}</h2><p>{latestWar.dados.teamSize} × {latestWar.dados.teamSize} · {latestWar.dados.state === "warEnded" ? "encerrada" : latestWar.dados.state === "inWar" ? "em disputa" : "em preparação"}</p></div><div className="planning-duel"><CvBars members={wwSide.members} label="Winning Wars escalado" /><CvBars members={currentOpponent.members} label={`${currentOpponent.name} escalado`} /></div></section>}
      <section className="section-block"><div className="section-title"><div><span className="eyebrow">Elencos inscritos</span><h2>Quantidade detalhada de CV por clã</h2><p>Distribuição completa do grupo de Liga informada pela Supercell.</p></div></div><div className="planning-clan-grid">{clans.map((clan) => <article className={clan.tag === MAIN_CLAN_TAG ? "ours" : ""} key={clan.tag}><header><div><small>{clan.tag === MAIN_CLAN_TAG ? "Nosso clã" : "Adversário"}</small><strong>{clan.name}</strong><span>{clan.tag}</span></div><b>{clan.members.length}</b></header><CvBars members={clan.members} label="Inscritos" /></article>)}</div></section>
      {!!opponents.length && <section className="section-block opponent-intelligence"><div className="section-title"><div><span className="eyebrow">Inteligência de batalha</span><h2>Perfil observado do adversário</h2><p>Estatísticas calculadas apenas com ataques disponibilizados pela API oficial.</p></div><label><span>Selecionar clã</span><select value={chosenTag} onChange={(event) => setOpponentTag(event.target.value)}>{opponents.map((clan) => <option key={clan.tag} value={clan.tag}>{clan.name} · {clan.tag}</option>)}</select></label></div>{chosen && <><div className="planning-metrics"><article><small>Guerras observadas</small><strong>{observedWars.length}</strong></article><article><small>Ataques registrados</small><strong>{observedAttacks.length}</strong></article><article><small>Taxa de três estrelas</small><strong>{observedAttacks.length ? `${Math.round((triples / observedAttacks.length) * 100)}%` : "—"}</strong></article><article><small>Destruição média</small><strong>{observedAttacks.length ? `${avgDestruction.toFixed(1)}%` : "—"}</strong></article><article><small>Duração média</small><strong>{durations.length ? `${Math.round(avgDuration)} s` : "—"}</strong></article></div><CvBars members={chosen.members} label={`${chosen.name} · elenco inscrito`} /></>}</section>}
      <div className="planning-disclaimer"><strong>Limite dos dados da Supercell</strong><span>A API informa CV, escalações, alvos, estrelas, destruição e duração. Ela não informa tropas, feitiços, máquinas ou composição do exército; por isso o app não inventa esses dados.</span></div>
    </>}
  </div>;
}

const CLAN_RULES = [
  "Novatos devem ser avaliados antes de participar das guerras do clã.",
  "Ataque uma vila do mesmo nível de Centro de Vila; o alvo não precisa ser o espelho.",
  "Três dias de inatividade sem aviso podem resultar em remoção do clã.",
  "Nos Jogos do Clã, faça no mínimo 2.000 pontos para permanecer elegível.",
  "Promoções e cargos são concedidos por mérito, participação e confiança.",
  "WhatsApp é obrigatório para Liga e para a competição dos passes.",
  "Contas muito apressadas ou com heróis incompatíveis com o CV podem não ser aceitas.",
  "Peça ajuda quando precisar e contribua para a evolução coletiva do clã.",
];

const PASS_RULES = [
  "A competição é mensal e usa somente pontuações validadas pelos motores e lançamentos administrativos auditados.",
  "A primeira pontuação positiva inscreve a conta automaticamente no ranking da temporada.",
  "O administrador pode habilitar apenas uma conta por jogador e bloquear contas secundárias quando necessário.",
  "Guerras, Liga e raides são processados automaticamente depois que a atividade termina e os dados são conferidos.",
  "Jogos do Clã e eventos sem retorno oficial da Supercell são lançados manualmente pelo administrador.",
  "Jogos do Clã: abaixo de 2.000 = 0; 2.000–3.999 = 2; 4.000–9.999 = 5; 10.000 = 10 pontos.",
  "Correções substituem o total da atividade; nunca somam o mesmo resultado duas vezes.",
  "Os três primeiros colocados elegíveis ao fim da temporada recebem o Passe Dourado, conforme validação da liderança.",
  "O motor preserva o desempenho de todas as contas nas atividades automáticas. Contas desabilitadas ficam fora do ranking oficial; ao habilitar, a contribuição validada aparece sem duplicar lançamentos.",
  "A tabela detalhada é pública. Fichas individuais e o arquivo técnico de batalhas são consultas administrativas protegidas.",
];

export function RulesPage() {
  return <div className="page rules-page"><PageHeader eyebrow="Código da fortaleza" title="Regras oficiais" description="Critérios claros para convivência no clã e participação na competição mensal dos passes." /><section className="rules-hero"><div><span>▤</span><h2>Competir com transparência.<br />Evoluir com respeito.</h2><p>Estas regras protegem a comunidade, a justiça do ranking e a organização das atividades.</p></div><img src={CREST_URL} alt="Brasão Winning Wars" /></section><div className="official-rules-grid"><section><header><span>01</span><div><small>Comunidade</small><h2>Regras do clã</h2></div></header><ol>{CLAN_RULES.map((rule, index) => <li key={rule}><b>{String(index + 1).padStart(2, "0")}</b><span>{rule}</span></li>)}</ol></section><section><header><span>02</span><div><small>Temporada mensal</small><h2>Competição dos passes</h2></div></header><ol>{PASS_RULES.map((rule, index) => <li key={rule}><b>{String(index + 1).padStart(2, "0")}</b><span>{rule}</span></li>)}</ol></section></div></div>;
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
  const { session } = useAdmin();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.torneio>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = () => { setLoading(true); setError(null); api.torneio().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao abrir a arena.")).finally(() => setLoading(false)); };
  useEffect(load, []);
  const torneio = data?.torneio;
  const roster = data?.roster;
  return <div className="page tournament-page">
    <section className="tournament-hero"><div><span className="eyebrow">Arena oficial para lives</span><h1>Torneios Winning Wars</h1><p>Confrontos eliminatórios 1 × 1, da primeira batalha à grande final.</p><div><span>TorneiosWWars · #2CY88CCYU</span><a href="https://www.youtube.com/@winningwarscoc" target="_blank" rel="noreferrer">▶ YouTube @winningwarscoc</a>{session.autenticado && <Link className="tournament-admin-cta" to="/admin/torneios">⚙ Iniciar ou controlar torneio</Link>}</div></div><img src={CREST_URL} alt="Brasão Winning Wars" /></section>
    <details className="rules-panel" open><summary>Regras oficiais do torneio</summary><ol>{REGRAS_TORNEIO.map((regra, index) => <li key={regra}><b>{String(index + 1).padStart(2, "0")}</b><span>{regra}</span></li>)}</ol></details>
    {loading && <Loading label="Conectando à arena oficial…" />}{error && <ErrorState message={error} onRetry={load} />}
    {!loading && !error && roster && <section className="roster-summary"><div><span className="eyebrow">Elenco em tempo real</span><h2>{roster.clan}</h2><p>{roster.contas.length} contas · {roster.tag}</p></div><div className="roster-cvs">{CVS.map((value) => { const total = roster.contas.filter((p) => p.cv === value).length; return total ? <span key={value}><img src={townHallUrl(value)} alt="" />CV {value}: <b>{total}</b></span> : null; })}</div></section>}
    {!loading && !error && !torneio && <div className="state-card tournament-empty"><strong>A arena está preparada para o próximo torneio</strong><span>O chaveamento aparecerá aqui assim que a organização iniciar a competição.</span></div>}
    {torneio && <><section className="tournament-title"><div><span className="eyebrow">Chaveamento oficial</span><h2>{torneio.nome}</h2><p>{torneio.participantes.length} competidores · CV {torneio.cv} · {torneio.modo}</p></div>{torneio.campeao && <div className="champion-chip">🏆 {torneio.campeao.nome}</div>}</section><div className="bracket">{torneio.rodadas.map((round, roundIndex) => <section className="bracket-round" key={roundIndex}><h3>{torneio.rotulos[roundIndex]}</h3><div>{round.map((match, index) => <TournamentMatchCard key={index} match={match} index={index} />)}</div></section>)}</div></>}
  </div>;
}

export function AdminTournamentPage() {
  const { session, loading: sessionLoading } = useAdmin();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.torneio>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("Torneios Winning Wars");
  const [mode, setMode] = useState("Desafio amistoso");
  const [cv, setCv] = useState<number | "Todos">("Todos");
  const [selected, setSelected] = useState<string[]>([]);
  const load = () => { setLoading(true); api.torneio().then((result) => { setData(result); setSelected(result.roster?.contas.map((player) => player.tag) || []); }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar torneio.")).finally(() => setLoading(false)); };
  useEffect(load, []);
  if (sessionLoading) return <div className="page"><Loading /></div>;
  if (!session.autenticado) return <div className="page"><ErrorState message="Entre como administrador para controlar o torneio." /></div>;
  const roster = data?.roster?.contas || [];
  const eligible = roster.filter((player) => cv === "Todos" || player.cv === cv);
  const pending = data?.torneio?.rodadas.flatMap((round, roundIndex) => round.map((match, matchIndex) => ({ roundIndex, matchIndex, match }))).filter((item) => !item.match.vencedor && item.match.jogadores.every(Boolean)) || [];
  const run = async (action: () => Promise<unknown>, message: string) => { setError(null); setNotice(""); try { await action(); setNotice(message); load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Operação não concluída."); } };
  return <div className="page admin-page tournament-console"><div className="admin-subnav"><Link to="/torneios">← Voltar à arena</Link><span>Console não exibido na transmissão</span></div><PageHeader eyebrow="Console do organizador" title="Controle do torneio" description="Sorteie o chaveamento, confirme os vencedores e avance cada classificado com auditoria na planilha." />{loading && <Loading />}{error && <ErrorState message={error} />}{notice && <div className="admin-success">✓ {notice}</div>}{data && !data.torneio && <section className="tournament-create"><label><span>Nome do torneio</span><input value={name} onChange={(event) => setName(event.target.value)} /></label><label><span>Modo de jogo</span><input value={mode} onChange={(event) => setMode(event.target.value)} /></label><label><span>Centro de Vila</span><select value={cv} onChange={(event) => { const value = event.target.value; const next = value === "Todos" ? "Todos" : Number(value); setCv(next); setSelected(roster.filter((player) => next === "Todos" || player.cv === next).map((player) => player.tag)); }}><option value="Todos">Todos os CVs</option>{[...new Set(roster.map((player) => player.cv))].sort((a, b) => b - a).map((value) => <option value={value} key={value}>Somente CV {value}</option>)}</select></label><div className="tournament-select-list">{eligible.map((player) => <label key={player.tag}><input type="checkbox" checked={selected.includes(player.tag)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, player.tag] : current.filter((tag) => tag !== player.tag))} /><img src={townHallUrl(player.cv)} alt="" /><span><b>{player.nome}</b><small>{player.tag} · CV {player.cv}</small></span></label>)}</div><button className="primary-button" disabled={selected.length < 2} onClick={() => run(() => api.adminTournamentStart(name, mode, cv, selected), "Chaveamento sorteado e publicado na arena.")}>🎲 Sortear e iniciar torneio ({selected.length})</button>{roster.length < 2 && <div className="planning-disclaimer"><strong>Elenco insuficiente</strong><span>A Oracle está conectada ao clã TorneiosWWars. O torneio poderá começar quando houver pelo menos dois participantes.</span></div>}</section>}{data?.torneio && <><section className="tournament-title"><div><span className="eyebrow">Torneio ativo</span><h2>{data.torneio.nome}</h2><p>{pending.length} confronto(s) aguardando resultado.</p></div><button className="secondary-button" onClick={() => run(api.adminTournamentReset, "Torneio encerrado. O console está pronto para um novo sorteio.")}>Encerrar e criar outro</button></section><div className="tournament-pending">{pending.map(({ roundIndex, matchIndex, match }) => <article key={`${roundIndex}-${matchIndex}`}><small>{data.torneio?.rotulos[roundIndex]} · Jogo {matchIndex + 1}</small><h3>{match.jogadores[0]?.nome} × {match.jogadores[1]?.nome}</h3><div>{match.jogadores.map((player) => player && <button className="primary-button" key={player.tag} onClick={() => run(() => api.adminTournamentWinner(roundIndex, matchIndex, player.tag), `${player.nome} avançou no chaveamento.`)}>Confirmar {player.nome}</button>)}</div></article>)}</div></>}</div>;
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
  const podium = ranking.filter((item) => item.posicao <= 3);
  const list = ranking.filter((item) => item.posicao > 3);
  return <div className="fortress-cv-ranking">
    <div className="fortress-prize"><span>🎟️</span><div><small>Competição Winning Wars</small><strong>Top 3 garantem o Passe Dourado</strong></div><b>Temporada em disputa</b></div>
    {!!podium.length && <div className="fortress-cv-podium">{podium.map((player) => <Link to={`/jogador/${encodeURIComponent(player.tag)}`} key={player.tag} className={`cv-podium-card place-${player.posicao}`}>
      <span className="cv-place">{player.posicao === 1 ? "🥇" : player.posicao === 2 ? "🥈" : "🥉"} {player.posicao}º lugar</span>
      <RankingTownHall player={player} />
      <div><strong>{player.nome}</strong><small>{player.tag}</small><span>⚔ {player.guerra} · ☄ {player.raides} · ♟ {player.jogos} · ◆ {player.eventos}</span></div>
      <b>{player.total}<small> pontos</small></b>
    </Link>)}</div>}
    {!!list.length && <div className="fortress-cv-list"><header><span>Pos.</span><span>Vila e jogador</span><span>Desempenho da temporada</span><span>Total</span></header>{list.map((player) => <Link to={`/jogador/${encodeURIComponent(player.tag)}`} key={player.tag} className="fortress-cv-row">
      <span className="cv-list-position">{player.posicao}</span>
      <span className="cv-list-player"><RankingTownHall player={player} compact /><span><strong>{player.nome}</strong><small>{player.tag}</small></span></span>
      <span className="cv-list-progress"><i style={{ width: `${Math.max(8, player.total / max * 100)}%` }} /><small>⚔ {player.guerra} guerras · ☄ {player.raides} raides · ♟ {player.jogos} jogos · ◆ {player.eventos} eventos</small></span>
      <b>{player.total}<small> pts</small></b>
    </Link>)}</div>}
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
      <aside className="admin-security-card"><span>Proteções ativas</span><ul><li>Cookie de sessão inacessível ao JavaScript</li><li>Validação do administrador a cada operação</li><li>Limite de tentativas de login</li><li>Credenciais do Google apenas na Oracle</li><li>Backup, auditoria e conferência após cada gravação</li></ul></aside>
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
    <div className="read-only-banner active-write"><span>✓</span><div><strong>Controles administrativos ativos</strong><small>As alterações autorizadas criam backup, auditoria e conferência na planilha oficial.</small></div></div>
    {loading && <Loading label="Carregando controles administrativos…" />}
    {error && <ErrorState message={error} />}
    {summary && <>
      <section className="admin-metrics">
        <article><small>Temporada</small><strong>{summary.temporada_nome || summary.temporada}</strong><span>{summary.ranking.jogadores} contas no ranking</span></article>
        <article><small>Participação</small><strong>{summary.participacao.habilitadas}</strong><span>contas habilitadas</span></article>
        <article><small>Bloqueios</small><strong>{summary.participacao.bloqueadas}</strong><span>decisões administrativas</span></article>
        <article><small>Nível de acesso</small><strong>{summary.admin.nivel}</strong><span>{summary.admin.usuario}</span></article>
      </section>
      <section className="admin-modules"><div className="section-title"><div><span className="eyebrow">Operação oficial</span><h2>Controles administrativos</h2><p>Módulos com acesso protegido, histórico e confirmação de gravação.</p></div></div><div>
        {["Participação e vínculos", "Jogos do Clã e eventos", "Torneios Winning Wars", "Revisões de pontuação", "Fechamento mensal"].map((label, index) => <article key={label}><span>{String(index + 1).padStart(2, "0")}</span><strong>{index === 0 ? <Link to="/admin/participacao">{label}</Link> : index === 1 ? <Link to="/admin/lancamentos">{label}</Link> : index === 2 ? <Link to="/admin/torneios">{label}</Link> : label}</strong><small>{index <= 2 ? "Ativo e auditado" : "Permanece no app legado durante a migração"}</small></article>)}
      </div></section>
    </>}
  </div>;
}

function linhasPreservadas(valor: string): string[] {
  const linhas = valor.split(/\r?\n/).map((linha) => linha.trim());
  while (linhas.length && !linhas[linhas.length - 1]) linhas.pop();
  return linhas;
}

async function otimizarLayout(file: File): Promise<string> {
  if (file.size > 10 * 1024 * 1024) throw new Error(`${file.name}: o arquivo excede 10 MB.`);
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) throw new Error(`${file.name}: formato não permitido.`);
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error(`${file.name}: não foi possível abrir a imagem.`));
      element.src = objectUrl;
    });
    const escala = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.naturalWidth * escala));
    canvas.height = Math.max(1, Math.round(image.naturalHeight * escala));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('O navegador não conseguiu processar as imagens.');
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
      (result) => result ? resolve(result) : reject(new Error(`${file.name}: falha ao converter para WEBP.`)),
      'image/webp', .82,
    ));
    if (blob.size > 1_600_000) throw new Error(`${file.name}: a imagem otimizada ainda excede 1,6 MB.`);
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(',', 2)[1] || '');
      reader.onerror = () => reject(new Error(`${file.name}: falha ao preparar o envio.`));
      reader.readAsDataURL(blob);
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function LayoutPublisher({ tipo, cv, onPublished }: { tipo: "Guerra" | "Rankeada"; cv: number; onPublished: () => void }) {
  const [links, setLinks] = useState("");
  const [descriptions, setDescriptions] = useState("");
  const [imageUrls, setImageUrls] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [progress, setProgress] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [duplicates, setDuplicates] = useState<AdminLayoutDuplicate[]>([]);

  const publish = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(null); setNotice(""); setDuplicates([]);
    const officialLinks = links.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const descriptionLines = linhasPreservadas(descriptions);
    const directUrls = linhasPreservadas(imageUrls);
    if (!officialLinks.length) return setError("Informe pelo menos um link oficial de layout.");
    if (officialLinks.length > 20) return setError("O limite é de 20 layouts por lote.");
    if (files.length > officialLinks.length) return setError("Há mais imagens do que links de layout.");
    if (descriptionLines.length > officialLinks.length || directUrls.length > officialLinks.length) return setError("Há mais descrições ou URLs de imagem do que links oficiais.");
    setSending(true);
    try {
      const imagens: string[] = [];
      for (let index = 0; index < files.length; index += 1) {
        setProgress(`Otimizando imagem ${index + 1} de ${files.length}…`);
        imagens.push(await otimizarLayout(files[index]));
      }
      setProgress(`Publicando ${officialLinks.length} layout(s) e conferindo a planilha…`);
      const result = await api.adminLayoutsBatch(tipo, cv, officialLinks.map((link, index) => ({
        link,
        descricao: descriptionLines[index] || "",
        imagem_base64: imagens[index] || "",
        imagem_url: imagens[index] ? "" : directUrls[index] || "",
      })));
      setNotice(`${result.aplicados} layout(s) de ${tipo} para CV ${cv} publicados e conferidos.`);
      setLinks(""); setDescriptions(""); setImageUrls(""); setFiles([]);
      onPublished();
    } catch (reason) {
      if (reason instanceof LayoutsDuplicadosError) setDuplicates(reason.itens);
      else setError(reason instanceof Error ? reason.message : "Não foi possível publicar os layouts.");
    } finally { setSending(false); setProgress(""); }
  };

  return <details className="layout-publisher" open>
    <summary><span><b>＋ Publicar em CV {cv}</b><small>Somente administradores · {tipo}</small></span><em>abrir/fechar</em></summary>
    <div className="layout-publisher-body">
    <div className="security-warning"><strong>Publicação em lote</strong><span>Adicione até 20 layouts de {tipo} para o CV {cv}. As imagens são otimizadas e armazenadas externamente; a planilha recebe somente os dados e URLs, com backup, auditoria e conferência.</span></div>
    {error && <div className="state-card error-state"><strong>Não foi possível publicar os layouts</strong><span>{error}</span></div>}
    {!!duplicates.length && <div className="layout-duplicate-alert"><header><strong>{duplicates.length === 1 ? "1 layout já está publicado" : `${duplicates.length} layouts já estão publicados`}</strong><span>Nenhum item do lote foi gravado. Remova as linhas indicadas e selecione novamente as imagens correspondentes.</span></header><ol>{duplicates.map((item) => <li key={`${item.linha_lote}-${item.link}`}><b>Linha {item.linha_lote}</b><span>{item.tipo || tipo} · {item.cv || `CV ${cv}`}{item.autor ? ` · publicado por ${item.autor}` : ""}</span><a href={item.link} target="_blank" rel="noreferrer">{item.link}</a></li>)}</ol></div>}
    {notice && <div className="admin-success">✓ {notice} A galeria foi atualizada.</div>}
    <form className="layouts-batch-form" onSubmit={publish}>
      <label><span>Links oficiais dos layouts — um por linha</span><textarea required rows={8} value={links} onChange={(event) => { setLinks(event.target.value); setDuplicates([]); }} placeholder={'https://link.clashofclans.com/pt?action=OpenLayout&id=...\nhttps://link.clashofclans.com/pt?action=OpenLayout&id=...'} /></label>
      <label className="layout-file-picker"><span>Imagens — selecione na mesma ordem dos links</span><input type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} /><small>PNG, JPG ou WEBP · máximo 10 MB por arquivo · até 20 imagens.</small></label>
      {!!files.length && <div className="selected-layout-files"><strong>{files.length} imagem(ns) selecionada(s)</strong>{files.map((file, index) => <span key={`${file.name}-${index}`}>{index + 1}. {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</span>)}</div>}
      <div className="layout-optional-grid"><label><span>Descrições opcionais — uma por linha</span><textarea rows={5} value={descriptions} onChange={(event) => setDescriptions(event.target.value)} placeholder="Base anti-3 estrelas\nBase para guerra convencional" /></label><label><span>URLs diretas de imagem — alternativa ao upload</span><textarea rows={5} value={imageUrls} onChange={(event) => setImageUrls(event.target.value)} placeholder="Deixe vazio quando selecionar arquivos." /></label></div>
      <footer><span>{progress || `${links.split(/\r?\n/).filter((line) => line.trim()).length} link(s) · ${files.length} imagem(ns)`}</span><button className="primary-button" type="submit" disabled={sending}>{sending ? "Processando lote…" : "Publicar e conferir layouts"}</button></footer>
    </form>
    </div>
  </details>;
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
  const [writingTag, setWritingTag] = useState("");
  const [notice, setNotice] = useState("");

  const loadParticipation = () => {
    if (sessionLoading || !session.autenticado) return;
    setLoading(true); setError(null);
    api.adminParticipation().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar participação.")).finally(() => setLoading(false));
  };
  useEffect(loadParticipation, [session.autenticado, sessionLoading]);

  const toggleParticipation = async (account: AdminParticipationAccount) => {
    if (!account.evento_id || writingTag) return;
    setWritingTag(account.tag); setError(null); setNotice("");
    try {
      const enable = account.habilitada !== "TRUE";
      await api.adminParticipationToggle(account.tag, enable, enable ? "Habilitada pelo painel administrativo" : "Desabilitada pelo painel administrativo", account.evento_id);
      setNotice(`${account.nome} foi ${enable ? "habilitada" : "desabilitada"} e a decisão foi auditada.`);
      await api.adminParticipation().then(setData);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível alterar a participação."); }
    finally { setWritingTag(""); }
  };

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
    <div className="admin-subnav"><Link to="/admin">← Voltar ao painel</Link><span>Controle ativo e auditado</span></div>
    <PageHeader eyebrow="Controle da competição" title="Participação e vínculos" description="Presença no clã é um alerta operacional. Somente uma decisão administrativa pode bloquear uma conta." />
    {loading && <Loading label="Conferindo contas, vínculos e presença…" />}
    {error && <ErrorState message={error} />}
    {notice && <div className="admin-success">✓ {notice}</div>}
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
        <div><button className={`status-chip participation-toggle ${account.habilitada === "FALSE" ? "blocked" : account.habilitada === "TRUE" ? "enabled" : "neutral"}`} onClick={() => toggleParticipation(account)} disabled={!account.evento_id || writingTag === account.tag}>{writingTag === account.tag ? "Gravando…" : account.habilitada === "TRUE" ? "Habilitada · clique para desabilitar" : "Desabilitada · clique para habilitar"}</button><small>{account.inscrita ? "Inscrita na temporada" : "Ainda não inscrita"}</small></div>
        <div className="decision-cell"><strong>{account.administrador || (account.origem_decisao === "CADASTRO" ? "Automática" : "—")}</strong><small>{account.motivo || "Nenhuma decisão administrativa"}</small></div>
        <b>{account.pontos}<small> pts</small>{account.contribuicao && <small className="contribution-breakdown">Guerras/Liga {account.contribuicao.guerra} · Raides {account.contribuicao.raides}<br />Jogos {account.contribuicao.jogos} · Eventos {account.contribuicao.eventos}</small>}</b>
      </article>)}</section>
      {!accounts.length && <div className="state-card"><strong>Nenhuma conta encontrada</strong><span>Altere a busca ou o filtro selecionado.</span></div>}
    </>}
  </div>;
}

export function AdminManualPage() {
  const { session, loading: sessionLoading } = useAdmin();
  const [data, setData] = useState<AdminManualResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tag, setTag] = useState("");
  const [activity, setActivity] = useState<"JogosCla" | "Eventos">("JogosCla");
  const [value, setValue] = useState("");
  const [proposal, setProposal] = useState<AdminManualProposal | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [batchValues, setBatchValues] = useState<Record<string, string>>({});
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [batchNotice, setBatchNotice] = useState("");
  const [historySearch, setHistorySearch] = useState("");
  const secure = window.isSecureContext;

  useEffect(() => {
    if (sessionLoading || !session.autenticado) return;
    setLoading(true); setError(null);
    api.adminManual().then((result) => { setData(result); setTag(result.contas.find((account) => account.habilitada === "TRUE")?.tag || result.contas[0]?.tag || ""); }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Falha ao carregar lançamentos.")).finally(() => setLoading(false));
  }, [session.autenticado, sessionLoading]);

  const history = useMemo(() => {
    const term = historySearch.trim().toLocaleLowerCase("pt-BR");
    return (data?.historico || []).filter((item) => !term || Object.values(item).join(" ").toLocaleLowerCase("pt-BR").includes(term));
  }, [data, historySearch]);

  const simulate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const number = Number(value);
    if (!secure || !Number.isInteger(number)) return;
    setSimulating(true); setError(null); setProposal(null);
    try { setProposal(await api.adminManualProposal(tag, activity, number)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível simular."); }
    finally { setSimulating(false); }
  };

  const applyBatch = async () => {
    if (!data || batchSubmitting) return;
    const entries = data.contas.filter((account) => batchValues[account.tag] !== undefined && batchValues[account.tag] !== "").map((account) => ({ tag: account.tag, nome: account.nome, valor: Number(batchValues[account.tag]) }));
    if (!entries.length || entries.some((entry) => !Number.isInteger(entry.valor))) { setError("Preencha ao menos uma conta usando somente números inteiros."); return; }
    setBatchSubmitting(true); setError(null); setBatchNotice("");
    try {
      const result = await api.adminManualBatch(activity, entries);
      setBatchNotice(`${result.aplicados || 0} lançamento(s) registrado(s), auditado(s) e conferido(s).`);
      setBatchValues({});
      setData(await api.adminManual());
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível registrar o lote."); }
    finally { setBatchSubmitting(false); }
  };

  if (sessionLoading) return <div className="page"><Loading label="Conferindo sessão administrativa…" /></div>;
  if (!session.autenticado) return <div className="page admin-page"><PageHeader eyebrow="Lançamentos manuais" title="Acesso protegido" description="Jogos do Clã, eventos e auditoria exigem autenticação." /><div className="state-card"><strong>Sessão administrativa necessária</strong><Link className="primary-button" to="/admin/login">Entrar como administrador</Link></div></div>;

  return <div className="page admin-page manual-admin-page">
    <div className="admin-subnav"><Link to="/admin">← Voltar ao painel</Link><span>Gravação auditada e conferida</span></div>
    <PageHeader eyebrow="Pontuação manual integrada" title="Jogos do Clã e eventos em lote" description="Preencha várias vilas de uma vez. Cada valor substitui o total da atividade e a operação é conferida na planilha oficial." />
    {loading && <Loading label="Carregando contas e auditoria manual…" />}
    {error && <ErrorState message={error} />}
    {data && <>
      <section className="manual-rules"><article><span>♟</span><div><small>Regra dos Jogos do Clã</small><strong>{data.regras.jogos}</strong></div></article><article><span>↻</span><div><small>Operação segura</small><strong>{data.regras.operacao}</strong></div></article></section>
      {batchNotice && <div className="admin-success">✓ {batchNotice}</div>}
      <section className="batch-manual"><header><div><span className="eyebrow">Lançamento oficial</span><h2>Preencher em lote</h2><p>Campos vazios não são alterados. Zero é um lançamento explícito.</p></div><label><span>Atividade do lote</span><select value={activity} onChange={(event) => { setActivity(event.target.value as "JogosCla" | "Eventos"); setBatchValues({}); }}><option value="JogosCla">Jogos do Clã</option><option value="Eventos">Evento manual</option></select></label></header><div className="batch-manual-grid">{data.contas.filter((account) => account.habilitada === "TRUE").map((account) => <label key={account.tag}><span>{account.cv ? <img src={townHallUrl(account.cv)} alt="" /> : <i>?</i>}<b>{account.nome}</b><small>{account.tag}</small></span><input aria-label={`Valor de ${account.nome}`} type="number" min="0" max={activity === "JogosCla" ? "10000" : "1000000"} step="1" placeholder="—" value={batchValues[account.tag] || ""} onChange={(event) => setBatchValues((current) => ({ ...current, [account.tag]: event.target.value }))} /></label>)}</div><footer><span>{Object.values(batchValues).filter((value) => value !== "").length} conta(s) preenchida(s)</span><button className="primary-button" onClick={applyBatch} disabled={batchSubmitting || !Object.values(batchValues).some((value) => value !== "")}>{batchSubmitting ? "Gravando e conferindo…" : "Registrar lote na planilha"}</button></footer></section>
      {!secure && <div className="security-warning"><strong>Simulação aguardando HTTPS</strong><span>Os dados podem ser consultados após o login, mas nenhuma proposta será transmitida por uma conexão HTTP.</span></div>}
      <section className="manual-workspace">
        <form className="manual-form" onSubmit={simulate}><span className="eyebrow">Nova proposta</span><h2>Simular lançamento</h2><label><span>Conta</span><select value={tag} onChange={(event) => { setTag(event.target.value); setProposal(null); }} disabled={!secure}>{data.contas.map((account) => <option value={account.tag} key={account.tag}>{account.nome} · {account.tag}{account.habilitada === "FALSE" ? " · bloqueada" : ""}</option>)}</select></label><label><span>Atividade</span><select value={activity} onChange={(event) => { setActivity(event.target.value as "JogosCla" | "Eventos"); setProposal(null); }} disabled={!secure}><option value="JogosCla">Jogos do Clã</option><option value="Eventos">Evento manual</option></select></label><label><span>{activity === "JogosCla" ? "Pontos feitos no jogo" : "Pontos na competição"}</span><input type="number" min="0" max={activity === "JogosCla" ? "10000" : "1000000"} step="1" value={value} onChange={(event) => { setValue(event.target.value); setProposal(null); }} disabled={!secure} /></label><button className="primary-button" type="submit" disabled={!secure || !tag || value === "" || simulating}>{simulating ? "Conferindo…" : "Gerar proposta sem enviar"}</button><small>Nenhum botão de gravação existe nesta versão.</small></form>
        <div className="manual-proposal">{proposal ? <><span className={`proposal-status ${proposal.status.toLowerCase()}`}>{proposal.status === "BLOQUEADO" ? "Lançamento bloqueado" : proposal.status === "ZERO_SEM_INSCRICAO" ? "Zero sem inscrição" : "Proposta conferida"}</span><div className="proposal-player">{proposal.conta.cv ? <img src={townHallUrl(proposal.conta.cv)} alt={`CV ${proposal.conta.cv}`} /> : <span>?</span>}<div><strong>{proposal.conta.nome}</strong><small>{proposal.conta.tag}</small></div></div><div className="proposal-numbers"><span><small>Informado</small><b>{proposal.informado}</b></span><span><small>Antes</small><b>{proposal.antes}</b></span><span><small>Depois</small><b>{proposal.depois}</b></span></div>{proposal.inscreveria && <div className="proposal-enrollment">Primeira pontuação positiva: criaria inscrição e vínculo automaticamente.</div>}{proposal.motivo && <div className="proposal-block">Motivo: {proposal.motivo}</div>}<footer>Simulação somente leitura · nenhum dado foi enviado</footer></> : <div className="proposal-empty"><span>◇</span><strong>A proposta aparecerá aqui</strong><small>Selecione a conta, atividade e valor para conferir o resultado.</small></div>}</div>
      </section>
      <section className="manual-history"><div className="section-title"><div><span className="eyebrow">Auditoria integrada</span><h2>Histórico de lançamentos</h2><p>{data.historico.length} registros com hash conferido.</p></div><label className="search-box"><span>⌕</span><input value={historySearch} onChange={(event) => setHistorySearch(event.target.value)} placeholder="Buscar tag, atividade ou admin" /></label></div><div className="manual-history-list"><header><span>Data</span><span>Conta</span><span>Atividade</span><span>Informado</span><span>Antes → Depois</span><span>Administrador</span></header>{history.slice(0, 100).map((item) => <article key={item.EventoID}><time>{dataAtividade(item.RegistradoEm)}</time><strong>{item.PlayerTag}</strong><span>{item.Atividade === "JogosCla" ? "Jogos do Clã" : "Evento"}</span><span>{item.ValorInformado}</span><b>{item.Antes} → {item.Depois}</b><small>{item.Administrador}</small></article>)}</div>{!history.length && <div className="state-card"><strong>Nenhum lançamento encontrado</strong></div>}</section>
    </>}
  </div>;
}

export function NotFoundPage() {
  return <div className="page"><div className="state-card"><strong>Página não encontrada</strong><Link className="primary-button" to="/">Voltar ao início</Link></div></div>;
}
