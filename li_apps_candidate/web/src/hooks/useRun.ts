import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { addItem, type RunBlock, type RunState } from "../workspace";

export type RunView = Omit<RunState, "blocks" | "items" | "cursor"> & { blocks: RunBlock[] };

const idle: RunView = {
  active: false, turning: false, status: null, round: null, revision: 0, steps: [], stop: null,
  can_resume: false, report: null, chat_revision: 0, blocks: [],
};

/** Follows one case's run: quick while something is working, slow otherwise. The cursor keeps each poll to what is new. */
export function useRun(caseId: string | undefined, revision: number | undefined, reload: (id: string) => void) {
  const [run, setRun] = useState<RunView>(idle);
  const cursor = useRef(0);
  const poke = useRef(() => {});
  useEffect(() => {
    setRun(idle);
    cursor.current = 0;
    if (!caseId) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      clearTimeout(timer);
      let delay = 6000;
      try {
        const next = await api.run(caseId, cursor.current);
        if (!live) return;
        cursor.current = next.cursor;
        delay = next.active || next.turning ? 1500 : 6000;
        setRun((previous) => {
          const known = new Map(previous.blocks.map((block) => [block.id, block.items]));
          const blocks = next.blocks.map((block) => ({ ...block, items: known.get(block.id) ?? [] }));
          for (const item of next.items) {
            const block = blocks.find((candidate) => candidate.id === item.block);
            if (block) block.items = addItem(block.items, item);
          }
          return { ...next, blocks };
        });
      } catch {
        // A failed poll only delays the next one.
      }
      if (live) timer = setTimeout(tick, delay);
    };
    poke.current = () => void tick();
    void tick();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [caseId]);
  useEffect(() => {
    if (revision !== undefined) poke.current();
  }, [revision]);
  useEffect(() => {
    if (caseId && run.chat_revision > (revision ?? 0)) reload(caseId);
  }, [run.chat_revision]);
  return {
    run,
    resume: async () => {
      if (caseId) await api.resumeRun(caseId);
      poke.current();
    },
    halt: async () => {
      if (caseId) await api.stopRun(caseId);
      poke.current();
    },
  };
}
