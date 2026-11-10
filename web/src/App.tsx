import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loading, Shell } from "./components";
import { RankingProvider } from "./RankingContext";
import { AdminProvider } from "./AdminContext";
import { AdminContributionRankingPage, AdminLoginPage, AdminManualPage, AdminPage, AdminParticipationPage, AdminTournamentPage, AuditPage, DetailedRankingPage, HomePage, IdentityLabPage, LayoutsPage, NotFoundPage, PlanningPage, PlayerPage, RankingPage, RulesPage, TournamentPage } from "./pages";
import { useAdmin } from "./AdminContext";
import type { ReactNode } from "react";

function AdminOnly({ children }: { children: ReactNode }) {
  const { session, loading } = useAdmin();
  if (loading) return <div className="page"><Loading label="Conferindo acesso administrativo…" /></div>;
  if (!session.autenticado) return <Navigate to="/admin/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || "/"}>
      <RankingProvider>
        <AdminProvider>
          <Routes>
            <Route element={<Shell />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/ranking" element={<RankingPage />} />
              <Route path="/ranking/detalhado" element={<DetailedRankingPage />} />
              <Route path="/jogador/:tag?" element={<AdminOnly><PlayerPage /></AdminOnly>} />
              <Route path="/auditoria" element={<AdminOnly><AuditPage /></AdminOnly>} />
              <Route path="/planejamento" element={<PlanningPage />} />
              <Route path="/layouts/:tipo" element={<LayoutsPage />} />
              <Route path="/torneios" element={<TournamentPage />} />
              <Route path="/regras" element={<RulesPage />} />
              <Route path="/conceitos" element={<IdentityLabPage />} />
              <Route path="/admin/login" element={<AdminLoginPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/admin/participacao" element={<AdminParticipationPage />} />
              <Route path="/admin/contribuicoes" element={<AdminOnly><AdminContributionRankingPage /></AdminOnly>} />
              <Route path="/admin/lancamentos" element={<AdminManualPage />} />
              <Route path="/admin/torneios" element={<AdminTournamentPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </AdminProvider>
      </RankingProvider>
    </BrowserRouter>
  );
}
