import React from "react";
import { motion } from "framer-motion";

interface ModeToggleProps {
  mode: string;
  continuousLoop: boolean;
  onSetMode: (mode: string) => void;
  onToggleLoop: () => void;
}

const ModeToggle = ({ mode, continuousLoop, onSetMode, onToggleLoop }: ModeToggleProps) => {
  return (
    <div className="absolute top-6 right-6 z-30 flex items-center gap-2">
      <motion.button
        onClick={() => onSetMode("smart")}
        className={`rounded-md px-3 py-1 text-xs font-medium ${mode === "smart" ? "bg-cyan-600/30 text-cyan-300" : "text-muted-foreground/60"}`}
        aria-pressed={mode === "smart"}
      >
        SMART
      </motion.button>

      <motion.button
        onClick={() => onSetMode("virtual")}
        className={`rounded-md px-3 py-1 text-xs font-medium ${mode === "virtual" ? "bg-cyan-600/20 text-cyan-200" : "text-muted-foreground/60"}`}
        aria-pressed={mode === "virtual"}
      >
        VIRTUAL
      </motion.button>

      <motion.button
        onClick={onToggleLoop}
        className={`rounded-md px-3 py-1 text-xs font-medium ${continuousLoop ? "bg-emerald-600/25 text-emerald-200" : "text-muted-foreground/50"}`}
        aria-pressed={continuousLoop}
      >
        LOOP
      </motion.button>
    </div>
  );
};

export default ModeToggle;
