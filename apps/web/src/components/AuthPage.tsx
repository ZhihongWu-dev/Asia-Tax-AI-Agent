import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, Globe2, ArrowLeft, MailCheck } from "lucide-react";
import Brand, { BrandMark } from "./Brand";
import { languages, nextLocale, useLocale } from "../locale";
import { request, ApiError } from "../api";
import type { User } from "../auth";

export default function AuthPage({ configured, initialError, recovery, onLogin, onRecovered }: {
  configured: boolean; initialError: string; recovery: boolean;
  onLogin: (user: User) => void; onRecovered: () => void;
}) {
  const { t, locale, setLocale } = useLocale();
  const next = nextLocale(locale);
  const [mode, setMode] = useState<"login" | "signup" | "recover" | "resend">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [sent, setSent] = useState(false);
  const [deadline, setDeadline] = useState(0);
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    if (!deadline) return;
    const tick = () => setRemaining(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [deadline]);
  function cooldown() { setRemaining(60); setDeadline(Date.now() + 60000); }
  async function resendEmail() {
    if (busy || remaining || !configured) return;
    setBusy(true); setError("");
    try {
      await request("/auth/resend", "POST", { email: email.trim() });
      setSent(true); cooldown();
    } catch (e) {
      const code = e instanceof ApiError ? e.code : "auth_unavailable";
      setError(code);
      if (code === "auth_rate_limited") cooldown();
    } finally { setBusy(false); }
  }
  const resendLabel = remaining ? t("Resend in {n}s").replace("{n}", String(remaining)) : t("Resend verification email");
  const errors: Record<string, string> = {
    auth_invalid: t("Incorrect credentials or an expired verification link."),
    email_not_confirmed: t("Please verify your email before signing in."),
    auth_rate_limited: t("Too many attempts. Please try again later."),
    password_rejected: t("Use a new password with at least 8 characters."),
    password_mismatch: t("The passwords do not match."),
    login_required: t("Your session has expired. Please sign in again."),
    auth_link_invalid: t("This link has expired. Please request a new one."),
    auth_not_configured: t("Email sign-in is being set up. Please try again later."),
  };
  function change(next: typeof mode) { setMode(next); setError(""); setSent(false); setPassword(""); setConfirm(""); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (mode === "resend" && !recovery) { await resendEmail(); return; }
    if ((recovery || mode === "signup") && password !== confirm) { setError("password_mismatch"); return; }
    setBusy(true); setError("");
    try {
      if (recovery) { await request("/auth/password", "POST", { password }); setPassword(""); setConfirm(""); onRecovered(); }
      else if (mode === "login") {
        const result = await request<{ user: User }>("/auth/login", "POST", { email: email.trim(), password });
        setPassword(""); onLogin(result.user);
      } else {
        await request(`/auth/${mode}`, "POST", mode === "recover" ? { email: email.trim() } : { email: email.trim(), password });
        setPassword(""); setConfirm(""); setSent(true);
        if (mode === "signup") cooldown();
      }
    } catch (e) { setError(e instanceof ApiError ? e.code : "auth_unavailable"); }
    finally { setBusy(false); }
  }
  const title = recovery ? t("Set a new password") : mode === "login" ? t("Welcome back") : mode === "signup" ? t("Create your account") : mode === "resend" ? t("Verify your email") : t("Reset your password");
  const action = recovery ? t("Save password") : mode === "login" ? t("Sign in") : mode === "signup" ? t("Create account") : mode === "resend" ? resendLabel : t("Send reset email");
  return <main className="auth-page">
    <section className="auth-story" aria-label="Taxrora">
      <Brand />
      <div className="auth-story-copy"><span className="auth-eyebrow">TAXRORA / {t("TAX INTELLIGENCE")}</span>
        <h1>{t("Clarity in tax.")}<br />{t("A better path forward.")}</h1>
        <p>{t("Start with facts and evidence. Make every next step clearer.")}</p>
      </div>
      <div className="ledger-art" aria-hidden="true"><BrandMark size={220} /><span /><span /><span /></div>
      <span className="auth-story-footer">{t("CLARITY · EVIDENCE · CONFIDENCE")}</span>
    </section>
    <section className="auth-main">
      <button className="language-toggle auth-language" onClick={() => setLocale(next)} aria-label={languages[next].switchTo}><Globe2 size={15} />{languages[next].name}</button>
      <div className="auth-form-wrap">
        <div className="auth-mobile-brand"><Brand /></div>
        <div className="auth-form-content" key={`${mode}-${recovery}-${sent}`}>
        {sent ? <div className="auth-sent">
          <MailCheck size={36} />
          <div role="status"><h2>{t("Check your inbox")}</h2><p>{t("If eligible, this address will receive a verification or password reset link. Check your spam folder too.")}</p></div>
          {error && <p className="auth-error" role="alert">{errors[error] || t("Unable to send. Please try again.")}</p>}
          {mode !== "recover" && <div className="auth-links">
            <button disabled={busy || remaining > 0 || !configured} onClick={resendEmail}>{busy ? t("Sending…") : resendLabel}</button>
            <button disabled={busy} onClick={() => change("resend")}>{t("Change email")}</button>
          </div>}
          <button className="auth-submit" disabled={busy} onClick={() => change("login")}>{t("Back to sign in")}<ArrowRight size={17} /></button>
        </div> : <>
          <h2>{title}</h2><p className="auth-subtitle">{recovery ? t("Then continue to your workspace.") : mode === "login" ? t("Continue your tax research.") : mode === "signup" ? t("Keep your conversations and research together.") : mode === "resend" ? t("Enter the email you registered with to request a new verification link.") : t("We’ll email you a password reset link.")}</p>
          <form onSubmit={submit}>
            {!recovery && <label className="auth-field">{t("Email")}<input type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} disabled={busy} /></label>}
            {(recovery || mode === "login" || mode === "signup") && <label className="auth-field">{t("Password")}<span className="auth-password"><input type={visible ? "text" : "password"} autoComplete={mode === "login" && !recovery ? "current-password" : "new-password"} placeholder={t("Enter your password")} value={password} onChange={e => setPassword(e.target.value)} required minLength={mode === "login" && !recovery ? 1 : 8} maxLength={128} disabled={busy} /><button type="button" onClick={() => setVisible(!visible)} aria-label={visible ? t("Hide password") : t("Show password")}>{visible ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>}
            {(recovery || mode === "signup") && <label className="auth-field">{t("Confirm password")}<input type={visible ? "text" : "password"} autoComplete="new-password" placeholder={t("Repeat password, at least 8 characters")} value={confirm} onChange={e => setConfirm(e.target.value)} required minLength={8} maxLength={128} disabled={busy} /></label>}
            {(error || !configured) && <p className="auth-error" role="alert">{errors[error || "auth_not_configured"] || t("Unable to complete this request. Please try again.")}</p>}
            {!configured && <button type="button" className="auth-refresh" onClick={() => location.reload()}>{t("Check connection again")}</button>}
            <button className="auth-submit" disabled={busy || !configured || (mode === "resend" && remaining > 0)} type="submit">{busy ? t("Please wait…") : action}{busy ? <span className="auth-loader" /> : <ArrowRight size={17} />}</button>
          </form>
          {!recovery && mode === "login" && ["email_not_confirmed", "auth_link_invalid"].includes(error) && <div className="auth-links"><button disabled={busy || !configured} onClick={() => change("resend")}>{t("Resend verification email")}</button></div>}
          {!recovery && <div className="auth-links">{mode === "login" ? <><button onClick={() => change("recover")} disabled={busy}>{t("Forgot password?")}</button><button onClick={() => change("signup")} disabled={busy}>{t("Create account")}</button></> : <button onClick={() => change("login")} disabled={busy}><ArrowLeft size={14} />{t("Back to sign in")}</button>}</div>}
        </>}
        </div>
      </div>
      <p className="auth-footer">{t("Professional judgments require adviser review.", "sign-in")}</p>
    </section>
  </main>;
}
