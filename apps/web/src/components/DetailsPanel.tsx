import HintButton from "./HintButton";
import { CircleHelp, X } from "lucide-react";
import { useLocale } from "../locale";

export default function DetailsPanel({ onClose }: { onClose: () => void }) {
  const { t } = useLocale();
  return (
    <section className="details-panel" aria-labelledby="panel-title">
      <header className="panel-header">
        <div>
          <CircleHelp size={18} />
          <h2 id="panel-title">{t("About Taxrora")}</h2>
        </div>
        <HintButton className="icon-button" aria-label={t("Close details")} onClick={onClose}>
          <X size={18} />
        </HintButton>
      </header>
      <div className="panel-body">
        <div className="about-content">
          <h3>Taxrora</h3>
          <p>{t("Cross-border dividend tax planning workspace.")}</p>
        </div>
      </div>
    </section>
  );
}
