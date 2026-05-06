import React from "react";
import MicButton from "@/components/MicButton";

type OrbState = "idle" | "listening" | "thinking" | "speaking";

interface VoiceControllerProps {
  orbState: OrbState;
  onToggle: () => void;
  accentHue?: number;
}

const VoiceController = ({ orbState, onToggle, accentHue = 190 }: VoiceControllerProps) => {
  return (
    <div className="absolute bottom-12 z-10">
      <MicButton isActive={orbState === "listening"} onToggle={onToggle} accentHue={accentHue} />
    </div>
  );
};

export default VoiceController;
