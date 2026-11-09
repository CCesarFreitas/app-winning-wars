import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Shell } from "./components";
import { RankingProvider } from "./RankingContext";
import { AdminProvider } from "./AdminContext";
import { AdminLoginPage, AdminPage, AdminParticipationPage, AuditPage, HomePage, IdentityLabPage, LayoutsPage, NotFoundPage, PlayerPage, RankingPage, TournamentPage } from "./pages";

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || "/"}>
      <RankingProvider>
        <AdminProvider>
          <Routes>
            <Route element={<Shell />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/ranking" element={<RankingPage />} />
              <Route path="/jogador/:tag?" element={<PlayerPage />} />
              <Route path="/auditoria" element={<AuditPage />} />
              <Route path="/layouts/:tipo" element={<LayoutsPage />} />
              <Route path="/torneios" element={<TournamentPage />} />
              <Route path="/conceitos" element={<IdentityLabPage />} />
              <Route path="/admin/login" element={<AdminLoginPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/admin/participacao" element={<AdminParticipationPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </AdminProvider>
      </RankingProvider>
    </BrowserRouter>
  );
}
