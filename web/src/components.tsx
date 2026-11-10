import { NavLink, Outlet } from "react-router-dom";
import { iniciais, temporadaLabel } from "./format";
import { useRanking } from "./RankingContext";
import { CREST_URL } from "./assets";
import { useAdmin } from "./AdminContext";

const nav = [
  { to: "/", icon: "⌂", label: "Quartel-general", image: "/assets/menu/barbarian-king.webp" },
  { to: "/ranking", icon: "♛", label: "Ranking oficial", image: "/assets/menu/archer-queen.webp" },
  { to: "/ranking/detalhado", icon: "▦", label: "Tabela detalhada", image: "/assets/menu/royal-champion.webp" },
  { to: "/jogador", icon: "⚔", label: "Ficha do jogador", image: "/assets/menu/grand-warden.webp", admin: true },
  { to: "/auditoria", icon: "◈", label: "Arquivo de batalhas", image: "/assets/menu/witch.webp", admin: true },
  { to: "/planejamento", icon: "⌖", label: "Planejador de guerras", image: "/assets/menu/minion-prince.webp" },
  { to: "/layouts/guerra", icon: "⬢", label: "Layouts de guerra", image: "/assets/menu/pekka.webp" },
  { to: "/layouts/rankeada", icon: "⌁", label: "Layouts de Liga", image: "/assets/menu/electro-dragon.webp" },
  { to: "/torneios", icon: "⚡", label: "Torneios", image: "/assets/menu/valkyrie.webp" },
  { to: "/regras", icon: "▤", label: "Regras oficiais", image: "/assets/menu/healer.webp" },
  { to: "/admin", icon: "◆", label: "Painel Admin", image: "/assets/menu/barbarian-king.webp", admin: true },
];

export function Shell() {
  const { ranking } = useRanking();
  const { session } = useAdmin();
  const visibleNav = nav.filter((item) => !item.admin || session.autenticado);
  const temporada = temporadaLabel(ranking[0]?.temporada);
  return (
    <div className="app-shell royal-shell">
      <header className="royal-header">
        <div className="brand royal-brand">
          <img className="brand-crest" src={CREST_URL} alt="Brasão Winning Wars" />
          <span>
            <strong>Winning Wars App</strong>
            <small>Evolução · Alto desempenho · Competitividade</small>
          </span>
        </div>
        <div className="royal-status">
          <span className="season-chip royal-season"><b>Temporada em disputa</b><strong>{temporada}</strong></span>
          <span className="engine-status"><i className="live-dot" />Ranking em tempo real</span>
        </div>
        <div className="topbar-actions royal-actions">
          <NavLink className="admin-access" to={session.autenticado ? "/admin" : "/admin/login"}>{session.autenticado ? `◆ ${session.usuario}` : "🔐 Entrar como administrador"}</NavLink>
          <a className="clan-link" href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y" target="_blank" rel="noreferrer">Visitar clã <span>↗</span></a>
        </div>
      </header>
      <nav className="royal-tabs" aria-label="Navegação principal">
        {visibleNav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"}>
            {item.image ? <img className="clash-nav-icon" src={item.image} alt="" /> : <span aria-hidden="true">{item.icon}</span>}
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="main-content royal-content">
        <Outlet />
      </main>
      <footer className="fan-content-footer">
        <span>Winning Wars é um projeto de fã não oficial.</span>
        <span>Heróis e tropas: <a href="https://github.com/ClashKingInc/ClashKingAssets" target="_blank" rel="noreferrer">ClashKing Assets</a> · elementos do jogo pertencem à Supercell.</span>
      </footer>
      <nav className="mobile-nav" aria-label="Navegação móvel">
        {[nav[0], nav[1], nav[2], nav.find((item) => item.to === "/planejamento")!, nav.find((item) => item.to === "/admin")!].filter((item) => !item.admin || session.autenticado).map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"}>
            {item.image ? <img src={item.image} alt="" /> : <span aria-hidden="true">{item.icon}</span>}
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
