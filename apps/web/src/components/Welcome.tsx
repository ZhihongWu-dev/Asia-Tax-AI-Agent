import {
  ArrowUpRight,
  BookOpen,
  Check,
  Coins,
  Landmark,
  ReceiptText,
  Scale,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { presets } from "../demo";

const icons: LucideIcon[] = [Landmark, Coins, ReceiptText];
export default function Welcome({
  onStarter,
}: {
  onStarter: (text: string) => void;
}) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome-eyebrow">
        <span /> YOUR TAX RESEARCH COMPANION
      </div>
      <div className="financial-art" aria-hidden="true">
        <div className="orbit orbit-one" />
        <div className="orbit orbit-two" />
        <div className="art-tile tile-book">
          <BookOpen size={23} strokeWidth={1.4} />
        </div>
        <div className="art-tile tile-coins">
          <Coins size={24} strokeWidth={1.4} />
        </div>
        <div className="art-main">
          <Landmark size={51} strokeWidth={1.15} />
          <span className="art-check">
            <Check size={13} />
          </span>
        </div>
        <div className="art-tile tile-scale">
          <Scale size={21} strokeWidth={1.4} />
        </div>
        <span className="art-plus plus-one">+</span>
        <span className="art-plus plus-two">+</span>
      </div>
      <h1 id="welcome-title">
        复杂税务，<span>从一次对话开始。</span>
      </h1>
      <p className="welcome-description">
        一起梳理案例事实，找到法规依据，明确下一步。
        <br />
        让你的每一个税务问题，都有清晰的研究起点。
      </p>
      <div className="welcome-features">
        <span>
          <ReceiptText size={15} />
          结构化事实
        </span>
        <i />
        <span>
          <BookOpen size={15} />
          官方资料索引
        </span>
        <i />
        <span>
          <ShieldCheck size={15} />
          人工复核提示
        </span>
      </div>
      <div className="starter-heading">
        <span>从一个虚构案例开始</span>
        <span>香港 FSIE</span>
      </div>
      <div className="starter-grid">
        {presets.map((p, index) => {
          const Icon = icons[index];
          return (
            <button
              key={p.type}
              className="starter-card"
              onClick={() => onStarter(p.text)}
            >
              <span className={`starter-icon icon-${index}`}>
                <Icon size={21} strokeWidth={1.6} />
              </span>
              <ArrowUpRight className="starter-arrow" size={16} />
              <strong>{p.title}</strong>
              <span>{p.caption}</span>
            </button>
          );
        })}
      </div>
      <p className="starter-note">选择一个示例，或在下方描述你的虚构案例</p>
    </section>
  );
}
