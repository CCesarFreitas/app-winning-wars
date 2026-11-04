import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { RankingEntry } from "./types";

interface RankingState {
  ranking: RankingEntry[];
  loading: boolean;
  error: string | null;
  recarregar: () => void;
}

const RankingContext = createContext<RankingState | null>(null);

export function RankingProvider({ children }: { children: ReactNode }) {
  const [ranking, setRanking] = useState<RankingEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const recarregar = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api
      .ranking()
      .then((result) => active && setRanking(result))
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Falha na consulta.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [revision]);

  const value = useMemo(
    () => ({ ranking, loading, error, recarregar }),
    [ranking, loading, error, recarregar],
  );

  return <RankingContext.Provider value={value}>{children}</RankingContext.Provider>;
}

export function useRanking() {
  const value = useContext(RankingContext);
  if (!value) throw new Error("useRanking deve ser usado dentro de RankingProvider.");
  return value;
}
