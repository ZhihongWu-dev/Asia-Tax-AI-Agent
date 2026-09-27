import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { en } from "./locales/en";
import { workflow, liveEn } from "./locales/workflow";

export type Locale = "zh" | "en";
export const languagePreferenceKey = "asiatax.language";
export function translate(text: string, locale: Locale): string {
  if (workflow[text]) return workflow[text][locale === "en" ? 1 : 0];
  return locale === "en" ? (liveEn[text] ?? en[text] ?? text) : text;
}
const LocaleContext = createContext({
  locale: "zh" as Locale,
  setLocale: (_locale: Locale) => {},
  t: (text: string): string => text,
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    try {
      return localStorage.getItem(languagePreferenceKey) === "en" ? "en" : "zh";
    } catch {
      return "zh";
    }
  });
  function setLocale(next: Locale) {
    setLocaleState(next);
    try {
      localStorage.setItem(languagePreferenceKey, next);
    } catch {
      /* Private browsing can disallow storage. */
    }
  }
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
    document.title =
      locale === "zh"
        ? "AsiaTax · 税务研究助手"
        : "AsiaTax · Tax Research Assistant";
  }, [locale]);
  return (
    <LocaleContext.Provider
      value={{ locale, setLocale, t: (text) => translate(text, locale) }}
    >
      {children}
    </LocaleContext.Provider>
  );
}
export function useLocale() {
  return useContext(LocaleContext);
}
