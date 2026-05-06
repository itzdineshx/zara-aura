import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ResponseDisplayProps {
  text: string;
  subtext?: string | null;
}

const ResponseDisplay = ({ text, subtext }: ResponseDisplayProps) => {
  return (
    <div className="absolute bottom-32 z-10 flex w-full flex-col items-center gap-2 px-6 text-center">
      <AnimatePresence mode="wait">
        <motion.p
          key={text}
          className="text-sm font-light text-foreground/90 tracking-wide"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
        >
          {text}
        </motion.p>
      </AnimatePresence>

      {subtext && (
        <motion.p
          className="text-xs font-thin text-muted-foreground/50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.22, duration: 0.45 }}
        >
          {subtext}
        </motion.p>
      )}
    </div>
  );
};

export default ResponseDisplay;
