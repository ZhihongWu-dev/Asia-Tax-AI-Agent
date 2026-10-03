import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, Globe2, ArrowLeft, MailCheck } from "lucide-react";
import Brand, { BrandMark } from "./Brand";
import { useLocale } from "../locale";
import { request, ApiError } from "../api";
import type { User } from "../auth";

export default function AuthPage({ configured, initialError, recovery, onLogin, onRecovered }: {
  configured: boolean; initialError: string; recovery: boolean;
  onLogin: (user: User) => void; onRecovered: () => void;
}) {
  const { locale, setLocale } = useLocale();
  const en = locale === "en";
  const say = (zh: string, english: string) => en ? english : zh;
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
  const resendLabel = remaining ? say(`${remaining} 秒后可重发`, `Resend in ${remaining}s`) : say("重新发送验证邮件", "Resend verification email");
  const errors: Record<string, string> = {
    auth_invalid: say("邮箱或密码不正确，或验证链接已失效。", "Incorrect credentials or an expired verification link."),
    email_not_confirmed: say("请先打开邮箱中的验证链接，再登录。", "Please verify your email before signing in."),
    auth_rate_limited: say("请求较频繁，请稍后重试。", "Too many attempts. Please try again later."),
    password_rejected: say("密码未满足要求，请使用至少 8 位的新密码。", "Use a new password with at least 8 characters."),
    password_mismatch: say("两次输入的密码不一致。", "The passwords do not match."),
    login_required: say("登录已过期，请重新登录。", "Your session has expired. Please sign in again."),
    auth_link_invalid: say("验证链接已失效，请重新申请。", "This link has expired. Please request a new one."),
    auth_not_configured: say("邮箱登录尚未配置完成，请稍后再试。", "Email sign-in is being set up. Please try again later."),
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
  const title = recovery ? say("设置新密码", "Set a new password") : mode === "login" ? say("欢迎回来", "Welcome back") : mode === "signup" ? say("创建你的账号", "Create your account") : mode === "resend" ? say("验证你的邮箱", "Verify your email") : say("找回密码", "Reset your password");
  const action = recovery ? say("保存新密码", "Save password") : mode === "login" ? say("登录", "Sign in") : mode === "signup" ? say("创建账号", "Create account") : mode === "resend" ? resendLabel : say("发送重置邮件", "Send reset email");
  return <main className="auth-page">
    <section className="auth-story" aria-label="Taxora">
      <Brand />
      <div className="auth-story-copy"><span className="auth-eyebrow">TAXORA / {say("税衡", "TAX INTELLIGENCE")}</span>
        <h1>{say("看清税务，", "Clarity in tax.")}<br />{say("找到更优路径。", "A better path forward.")}</h1>
        <p>{say("从事实与依据出发，让每一步判断更清晰。", "Start with facts and evidence. Make every next step clearer.")}</p>
      </div>
      <div className="ledger-art" aria-hidden="true"><BrandMark size={220} /><span /><span /><span /></div>
      <span className="auth-story-footer">{say("清晰 · 有据 · 从容", "CLARITY · EVIDENCE · CONFIDENCE")}</span>
    </section>
    <section className="auth-main">
      <button className="language-toggle auth-language" onClick={() => setLocale(en ? "zh" : "en")} aria-label={en ? "切换为中文" : "Switch to English"}><Globe2 size={15} />{en ? "中文" : "EN"}</button>
      <div className="auth-form-wrap">
        <div className="auth-mobile-brand"><Brand /></div>
        <div className="auth-form-content" key={`${mode}-${recovery}-${sent}`}>
        {sent ? <div className="auth-sent">
          <MailCheck size={36} />
          <div role="status"><h2>{say("请查看邮箱", "Check your inbox")}</h2><p>{say("如果该邮箱可以接收此邮件，你将收到验证或密码重置链接。也请检查垃圾邮件。", "If eligible, this address will receive a verification or password reset link. Check your spam folder too.")}</p></div>
          {error && <p className="auth-error" role="alert">{errors[error] || say("暂时无法发送，请稍后重试。", "Unable to send. Please try again.")}</p>}
          {mode !== "recover" && <div className="auth-links">
            <button disabled={busy || remaining > 0 || !configured} onClick={resendEmail}>{busy ? say("正在发送…", "Sending…") : resendLabel}</button>
            <button disabled={busy} onClick={() => change("resend")}>{say("修改邮箱", "Change email")}</button>
          </div>}
          <button className="auth-submit" disabled={busy} onClick={() => change("login")}>{say("返回登录", "Back to sign in")}<ArrowRight size={17} /></button>
        </div> : <>
          <h2>{title}</h2><p className="auth-subtitle">{recovery ? say("设置后即可继续使用你的工作空间。", "Then continue to your workspace.") : mode === "login" ? say("继续你的税务研究。", "Continue your tax research.") : mode === "signup" ? say("保存对话，让研究有迹可循。", "Keep your conversations and research together.") : mode === "resend" ? say("输入注册时使用的邮箱，重新申请验证链接。", "Enter the email you registered with to request a new verification link.") : say("我们会向你的邮箱发送重置链接。", "We’ll email you a password reset link.")}</p>
          <form onSubmit={submit}>
            {!recovery && <label className="auth-field">{say("邮箱", "Email")}<input type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} disabled={busy} /></label>}
            {(recovery || mode === "login" || mode === "signup") && <label className="auth-field">{say("密码", "Password")}<span className="auth-password"><input type={visible ? "text" : "password"} autoComplete={mode === "login" && !recovery ? "current-password" : "new-password"} placeholder={say("请输入密码", "Enter your password")} value={password} onChange={e => setPassword(e.target.value)} required minLength={mode === "login" && !recovery ? 1 : 8} maxLength={128} disabled={busy} /><button type="button" onClick={() => setVisible(!visible)} aria-label={visible ? say("隐藏密码", "Hide password") : say("显示密码", "Show password")}>{visible ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>}
            {(recovery || mode === "signup") && <label className="auth-field">{say("确认密码", "Confirm password")}<input type={visible ? "text" : "password"} autoComplete="new-password" placeholder={say("再次输入密码，至少 8 位", "Repeat password, at least 8 characters")} value={confirm} onChange={e => setConfirm(e.target.value)} required minLength={8} maxLength={128} disabled={busy} /></label>}
            {(error || !configured) && <p className="auth-error" role="alert">{errors[error || "auth_not_configured"] || say("暂时无法完成请求，请稍后重试。", "Unable to complete this request. Please try again.")}</p>}
            {!configured && <button type="button" className="auth-refresh" onClick={() => location.reload()}>{say("重新检查连接", "Check connection again")}</button>}
            <button className="auth-submit" disabled={busy || !configured || (mode === "resend" && remaining > 0)} type="submit">{busy ? say("正在处理…", "Please wait…") : action}{busy ? <span className="auth-loader" /> : <ArrowRight size={17} />}</button>
          </form>
          {!recovery && mode === "login" && ["email_not_confirmed", "auth_link_invalid"].includes(error) && <div className="auth-links"><button disabled={busy || !configured} onClick={() => change("resend")}>{say("重新发送验证邮件", "Resend verification email")}</button></div>}
          {!recovery && <div className="auth-links">{mode === "login" ? <><button onClick={() => change("recover")} disabled={busy}>{say("忘记密码？", "Forgot password?")}</button><button onClick={() => change("signup")} disabled={busy}>{say("创建账号", "Create account")}</button></> : <button onClick={() => change("login")} disabled={busy}><ArrowLeft size={14} />{say("返回登录", "Back to sign in")}</button>}</div>}
        </>}
        </div>
      </div>
      <p className="auth-footer">{say("专业判断，由税务顾问复核。", "Professional judgments require adviser review.")}</p>
    </section>
  </main>;
}
