import { NavLink, Outlet } from "react-router-dom";
import { iniciais } from "./format";

const nav = [
  { to: "/", icon: "⌂", label: "Início" },
  { to: "/ranking", icon: "♛", label: "Ranking" },
  { to: "/jogador", icon: "♙", label: "Jogador" },
  { to: "/auditoria", icon: "◎", label: "Auditoria" },
];

export function Shell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">WW</span>
          <span>
            <strong>Winning Wars</strong>
            <small>Plataforma independente</small>
          </span>
        </div>
        <nav className="desktop-nav" aria-label="Navegação principal">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="live-dot" />
          Dados oficiais em modo somente leitura
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark small">WW</span> Winning Wars</div>
          <span className="readonly-chip">POC · somente leitura</span>
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
      {iniciais(nome).toUpperCase()}
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
