import React from "react";
import { motion } from "framer-motion";

type Device = { id: string; label: string; on: boolean };

interface DeviceControlPanelProps {
  devices?: Device[];
  onToggleDevice?: (id: string) => void;
}

const DeviceControlPanel = ({ devices = [], onToggleDevice }: DeviceControlPanelProps) => {
  return (
    <div className="absolute left-6 top-20 z-20 w-44 rounded-lg bg-white/3 backdrop-blur-md p-3">
      <h4 className="text-xs font-semibold text-foreground/90">Devices</h4>
      <div className="mt-2 flex flex-col gap-2">
        {devices.length === 0 && <p className="text-xs text-muted-foreground/60">No devices</p>}
        {devices.map((d) => (
          <motion.div key={d.id} className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{d.label}</div>
              <div className="text-xs text-muted-foreground/60">{d.on ? "On" : "Off"}</div>
            </div>
            <button
              onClick={() => onToggleDevice?.(d.id)}
              className={`h-8 w-12 rounded-full ${d.on ? "bg-emerald-400/80" : "bg-neutral-700/40"}`}
              aria-pressed={d.on}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default DeviceControlPanel;
