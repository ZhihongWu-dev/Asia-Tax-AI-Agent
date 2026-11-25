import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { errors } from "./locales/errors";
import { zh } from "./locales/zh";

// English is the source language: components pass English text to t(), and each translation maps that text to its own
// language. Adding a language means one file in locales/ and one entry in `languages`.
export type Translation = {
  name: string; // the toggle's label for switching to this language
  switchTo: string; // the toggle's accessible name, written in this language
  lang: string; // <html lang>
  strings: Record<string, string>; // English text, or "context|English text", to the translation
};
const english: Translation = { name: "EN", switchTo: "Switch to English", lang: "en", strings: {} };
export const languages = { en: english, zh } satisfies Record<string, Translation>;
export type Locale = keyof typeof languages;
export const defaultLocale: Locale = "en";
export const languagePreferenceKey = "taxrora.language";

const own = (map: Record<string, string>, key: string) =>
  Object.prototype.hasOwnProperty.call(map, key) ? map[key] : undefined;
const isLocale = (value: string | null): value is Locale =>
  value !== null && Object.prototype.hasOwnProperty.call(languages, value);

// `context` separates one English text that takes two wordings in a translation (e.g. "Progress" on the toggle and as
// the run panel's title); without an entry for the context the plain text is used.
export function translate(text: string, locale: Locale, context?: string): string {
  const source = own(errors, text) ?? text;
  const strings = languages[locale].strings;
  return (context && own(strings, `${context}|${source}`)) || own(strings, source) || source;
}
// The language the toggle switches to: the next one in `languages`.
export function nextLocale(locale: Locale): Locale {
  const all = Object.keys(languages) as Locale[];
  return all[(all.indexOf(locale) + 1) % all.length];
}

const LocaleContext = createContext({
  locale: defaultLocale as Locale,
  setLocale: (_locale: Locale) => {},
  t: (text: string, _context?: string): string => text,
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    try {
      const stored = localStorage.getItem(languagePreferenceKey);
      return isLocale(stored) ? stored : defaultLocale;
    } catch {
      return defaultLocale;
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
    document.documentElement.lang = languages[locale].lang;
    document.title = translate("Taxrora · Tax Planning", locale);
  }, [locale]);
  return (
    <LocaleContext.Provider
      value={{ locale, setLocale, t: (text, context) => translate(text, locale, context) }}
    >
      {children}
    </LocaleContext.Provider>
  );
}
export function useLocale() {
  return useContext(LocaleContext);
}
