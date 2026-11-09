import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Shell } from "./components";
import { RankingProvider } from "./RankingContext";
import { AuditPage, HomePage, NotFoundPage, PlayerPage, RankingPage } from "./pages";

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
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </RankingProvider>
    </BrowserRouter>
  );
}
