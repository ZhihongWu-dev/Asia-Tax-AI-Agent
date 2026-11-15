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
          <h2 id="panel-title">{t("关于 Taxrora")}</h2>
        </div>
        <HintButton className="icon-button" aria-label={t("关闭详情")} onClick={onClose}>
          <X size={18} />
        </HintButton>
      </header>
      <div className="panel-body">
        <div className="about-content">
          <h3>Taxrora</h3>
          <p>{t("跨境股息税务筹划工作空间。")}</p>
        </div>
      </div>
    </section>
  );
}
