import { writable } from "svelte/store";

import { api } from "../api/client";
import type { CalibrationValue, HardwareStatus, Job } from "../api/types";
import { events } from "../ws/client";

export const hardwareStatus = writable<HardwareStatus | null>(null);
export const activeJob = writable<Job | null>(null);
export const calibration = writable<CalibrationValue>("unknown");
export const connectionState = writable<"offline" | "online">("offline");
export const plannerConfiguration = writable<Configuration | null>(null);

export async function refreshStatus() {
  try {
    const status = await api.hardwareStatus();
    hardwareStatus.set(status);
    calibration.set(status.calibration.state);
    activeJob.set(await api.activeJob());
    connectionState.set("online");
  } catch (e) {
    console.error("Failed to refresh status", e);
    connectionState.set("offline");
  }
}

export function startEventStream() {
  events.subscribe(["*"], (frame) => {
    if (frame.topic === "hardware.status") {
      const status = frame.payload as HardwareStatus;
      hardwareStatus.set(status);
      calibration.set(status.calibration.state);
    } else if (frame.topic === "hardware.calibration") {
      const payload = frame.payload as { state: CalibrationValue };
      calibration.set(payload.state);
    } else if (frame.topic.startsWith("job.")) {
      if (frame.topic.endsWith(".state")) {
        activeJob.set(frame.payload as Job);
      } else if (frame.topic.endsWith(".progress")) {
        const progress = (frame.payload as Job).progress;
        activeJob.update((j) => (j ? { ...j, progress } : null));
      }
    }
  });
}
