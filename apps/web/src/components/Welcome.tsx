import { BrandMark } from "./Brand";
import { useLocale } from "../locale";

export default function Welcome() {
  const { t } = useLocale();
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome-mark" aria-hidden="true">
        <BrandMark size={38} />
      </div>
      <h1 id="welcome-title">{t("Clarity for your tax questions.")}</h1>
      <p>{t("Explore the facts and sources. Start a conversation.")}</p>
    </section>
  );
}
