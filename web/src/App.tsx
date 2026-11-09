import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Shell } from "./components";
import { RankingProvider } from "./RankingContext";
import { AuditPage, HomePage, IdentityLabPage, LayoutsPage, NotFoundPage, PlayerPage, RankingPage, TournamentPage } from "./pages";

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || "/"}>
      <RankingProvider>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/ranking" element={<RankingPage />} />
            <Route path="/jogador/:tag?" element={<PlayerPage />} />
            <Route path="/auditoria" element={<AuditPage />} />
            <Route path="/layouts/:tipo" element={<LayoutsPage />} />
            <Route path="/torneios" element={<TournamentPage />} />
            <Route path="/conceitos" element={<IdentityLabPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </RankingProvider>
    </BrowserRouter>
  );
}
