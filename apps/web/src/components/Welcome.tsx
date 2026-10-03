import { BookOpen, Landmark, ListChecks } from "lucide-react";
import { BrandMark } from "./Brand";
import { suggestions } from "../workspace";
import { useLocale } from "../locale";

export default function Welcome() {
  const { t } = useLocale();
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome-mark" aria-hidden="true">
        <BrandMark size={38} />
      </div>
      <h1 id="welcome-title">{t("让税务问题，更清晰。")}</h1>
      <p>{t("梳理事实，查阅依据，从一次对话开始。")}</p>
    </section>
  );
}
export function SuggestedQuestions({
  onSelect,
}: {
  onSelect: (text: string) => void;
}) {
  const { t } = useLocale();
  const icons = [Landmark, ListChecks, BookOpen];
  return (
    <div className="suggested-questions" aria-label={t("快捷问题")}>
      {suggestions.map((suggestion, i) => {
        const Icon = icons[i];
        return (
          <button
            key={suggestion.id}
            onClick={() => onSelect(t(suggestion.text))}
          >
            <Icon size={15} strokeWidth={1.5} />
            {t(suggestion.title)}
          </button>
        );
      })}
    </div>
  );
}
