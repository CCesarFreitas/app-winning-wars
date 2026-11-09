import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";
import type { AdminSession } from "./types";

interface AdminContextValue {
  session: AdminSession;
  loading: boolean;
  refresh: () => Promise<void>;
}

const AdminContext = createContext<AdminContextValue | null>(null);

export function AdminProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AdminSession>({ autenticado: false });
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      setSession(await api.adminSession());
    } catch {
      setSession({ autenticado: false });
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const value = useMemo(() => ({ session, loading, refresh }), [session, loading, refresh]);
  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}

export function useAdmin() {
  const context = useContext(AdminContext);
  if (!context) throw new Error("AdminProvider ausente");
  return context;
}
