import { NavLink, Outlet } from "react-router-dom";
import { iniciais, temporadaLabel } from "./format";
import { useRanking } from "./RankingContext";
import { CREST_URL } from "./assets";

const nav = [
  { to: "/", icon: "⌂", label: "Quartel-general" },
  { to: "/ranking", icon: "♛", label: "Ranking oficial" },
  { to: "/jogador", icon: "⚔", label: "Ficha do jogador" },
  { to: "/auditoria", icon: "◈", label: "Arquivo de batalhas" },
];

export function Shell() {
  const { ranking } = useRanking();
  const temporada = temporadaLabel(ranking[0]?.temporada);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-crest" src={CREST_URL} alt="Brasão Winning Wars" />
          <span>
            <strong>Winning Wars</strong>
            <small>Clash · Compete · Conquer</small>
          </span>
        </div>
        <div className="season-seal"><span>Temporada</span><strong>{temporada}</strong></div>
        <nav className="desktop-nav" aria-label="Navegação principal">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span><i className="live-dot" />Motor Winning Wars online</span>
          <small>Resultados validados pela Oracle</small>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand"><img src={CREST_URL} alt="" /> <span>Winning Wars</span></div>
          <div className="topbar-actions">
            <span className="season-chip">{temporada}</span>
            <a className="clan-link" href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y" target="_blank" rel="noreferrer">Visitar clã <span>↗</span></a>
          </div>
        </header>
        <Outlet />
      </main>
      <nav className="mobile-nav" aria-label="Navegação móvel">
        {nav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"}>
            <span aria-hidden="true">{item.icon}</span>
            <small>{item.label}</small>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="page-header">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

export function PlayerAvatar({ nome, position }: { nome: string; position?: number }) {
  return (
    <span className={`player-avatar ${position && position <= 3 ? `podium-${position}` : ""}`}>
      {position && position <= 3 ? <b>{position}</b> : iniciais(nome).toUpperCase()}
    </span>
  );
}

export function Loading({ label = "Consultando dados oficiais…" }: { label?: string }) {
  return <div className="state-card"><span className="spinner" />{label}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-card error-state">
      <strong>Não foi possível carregar os dados</strong>
      <span>{message}</span>
      {onRetry && <button className="secondary-button" onClick={onRetry}>Tentar novamente</button>}
    </div>
  );
}
