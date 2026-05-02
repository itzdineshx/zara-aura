import { useState, useCallback } from "react";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export default function useAIState(initial = { state: "idle" as OrbState, text: "Hello, I'm ZARA.", subtext: "Continuous loop is active. ZARA will keep listening." }) {
  const [state, setState] = useState<OrbState>(initial.state);
  const [text, setText] = useState<string>(initial.text);
  const [subtext, setSubtext] = useState<string | null>(initial.subtext ?? null);

  const setListening = useCallback(() => setState("listening"), []);
  const setThinking = useCallback(() => setState("thinking"), []);
  const setSpeaking = useCallback(() => setState("speaking"), []);
  const setIdle = useCallback(() => setState("idle"), []);

  return {
    state,
    text,
    subtext,
    setText,
    setSubtext,
    setListening,
    setThinking,
    setSpeaking,
    setIdle,
    setState,
  };
}
