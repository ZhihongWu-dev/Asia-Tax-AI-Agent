import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { request } from "./api";
import AuthPage from "./components/AuthPage";
import BrandLoader from "./components/BrandLoader";
import { useLocale } from "./locale";

export type User = { id: string; email: string };
const AuthContext = createContext({ user: null as User | null, logout: async () => {} });
export const useAuth = () => useContext(AuthContext);
export default function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useLocale();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [error, setError] = useState("");
  const [reset, setReset] = useState(new URLSearchParams(location.search).has("reset"));
  const boot = useRef<Promise<{ configured: boolean; user: User | null }> | null>(null);
  useEffect(() => {
    let live = true;
    boot.current ||= (async () => {
      const params = new URLSearchParams(location.hash.slice(1));
      const access = params.get("access_token"), refresh = params.get("refresh_token");
      if (access || params.has("error")) {
        history.replaceState(null, "", location.pathname + location.search);
        try {
          if (params.has("error") || !access || !refresh) throw new Error("auth_link_invalid");
          await request("/auth/callback", "POST", { access_token: access, refresh_token: refresh });
          if (params.get("type") === "recovery") {
            history.replaceState(null, "", "?reset=1");
            setReset(true);
          }
        } catch (failure) {
          const code = (failure as { code?: string }).code;
          setError(code && !["auth_invalid", "email_not_confirmed"].includes(code) ? code : "auth_link_invalid");
          setReset(false);
          const clean = new URL(location.href);
          clean.searchParams.delete("reset");
          history.replaceState(null, "", clean.pathname + clean.search);
        }
      }
      return request<{ configured: boolean; user: User | null }>("/auth/session");
    })();
    boot.current.then(data => { if (live) { setConfigured(data.configured); setUser(data.user); } })
      .catch(e => { if (live) setError(e.code || e.message || "auth_unavailable"); })
      .finally(() => { if (live) setLoading(false); });
    const expired = () => { setUser(null); setError("login_required"); };
    window.addEventListener("taxora:unauthorized", expired);
    const changed = (event: StorageEvent) => { if (event.key === "taxora.auth-change") location.reload(); };
    window.addEventListener("storage", changed);
    return () => { live = false; window.removeEventListener("taxora:unauthorized", expired); window.removeEventListener("storage", changed); };
  }, []);
  function announce() { try { localStorage.setItem("taxora.auth-change", crypto.randomUUID()); } catch { /* Storage can be disabled. */ } }
  async function logout() {
    await request("/auth/logout", "POST");
    setUser(null); setReset(false); setError("");
    history.replaceState(null, "", "/");
    announce();
  }
  if (loading) return <main className="startup"><BrandLoader fullPage label={t("正在载入工作空间…")} /></main>;
  if (!user || reset) return <AuthPage configured={configured} initialError={error} recovery={reset && !!user}
    onLogin={next => { setUser(next); setError(""); history.replaceState(null, "", "/"); announce(); }}
    onRecovered={() => { setReset(false); history.replaceState(null, "", "/"); }} />;
  return <AuthContext.Provider value={{ user, logout }}><div key={user.id} className="authenticated-shell">{children}</div></AuthContext.Provider>;
}
