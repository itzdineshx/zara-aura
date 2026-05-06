import React from "react";
import { motion } from "framer-motion";
import Orb from "@/components/Orb";

type OrbState = "idle" | "listening" | "thinking" | "speaking";

interface ZaraCoreProps {
  state: OrbState;
  audioStream?: MediaStream | null;
  visuals?: { hue: number; intensity: number; reactivity: number; dimmed?: boolean };
  title?: string;
  subtitle?: string | null;
}

const ZaraCore = ({ state, audioStream, visuals, title = "Hello, I'm ZARA.", subtitle }: ZaraCoreProps) => {
  return (
    <div className="relative z-10 flex flex-1 flex-col items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="flex items-center justify-center"
      >
        <Orb state={state} audioStream={audioStream} visuals={visuals} />
      </motion.div>

      <div className="absolute bottom-40 z-20 flex w-full flex-col items-center px-6 text-center">
        <motion.h2
          className="text-lg font-medium text-foreground/95"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
        >
          {title}
        </motion.h2>
        {subtitle !== undefined && subtitle !== null && (
          <motion.p
            className="mt-2 text-xs font-light text-muted-foreground/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.28 }}
          >
            {subtitle}
          </motion.p>
        )}
      </div>
    </div>
  );
};

export default ZaraCore;
