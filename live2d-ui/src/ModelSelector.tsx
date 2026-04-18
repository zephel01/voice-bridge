import { useEffect, useRef, useState } from "react";

export interface ModelEntry {
  id: string;
  name: string;
  path: string;
}

interface ModelSelectorProps {
  currentModelPath: string;
  onSelect: (model: ModelEntry) => void;
}

export function ModelSelector({ currentModelPath, onSelect }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // models.json を取得
  useEffect(() => {
    fetch("/live2d/models.json")
      .then((r) => r.json())
      .then((data: ModelEntry[]) => setModels(data))
      .catch((e) => console.warn("[ModelSelector] models.json の読み込みに失敗:", e));
  }, []);

  // パネル外クリックで閉じる
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (models.length <= 1) return null;

  const currentModel = models.find((m) => m.path === currentModelPath);

  return (
    <div className="model-selector" ref={panelRef}>
      <button
        className={`model-selector__toggle ${open ? "model-selector__toggle--open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        title="モデルを切り替える"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
        </svg>
        <span>{currentModel?.name ?? "Model"}</span>
        <svg
          className="model-selector__chevron"
          xmlns="http://www.w3.org/2000/svg"
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="model-selector__panel">
          <div className="model-selector__label">モデルを選択</div>
          {models.map((model) => {
            const isActive = model.path === currentModelPath;
            return (
              <button
                key={model.id}
                className={`model-selector__item ${isActive ? "model-selector__item--active" : ""}`}
                onClick={() => {
                  setOpen(false);
                  if (!isActive) onSelect(model);
                }}
              >
                <span className="model-selector__item-dot" />
                {model.name}
                {isActive && <span className="model-selector__item-check">✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
