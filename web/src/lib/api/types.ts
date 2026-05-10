import type { components } from "./generated";

export type HardwareState = components["schemas"]["CameraStatus"]["state"];
export type CalibrationValue = components["schemas"]["HardwareStatus"]["calibration"]["state"];
export type JobStatus = components["schemas"]["Job"]["status"];
export type CameraSettings = Record<string, SettingDescriptor>;

export interface SettingDescriptor {
  full_path: string;
  label: string;
  type: "TEXT" | "RANGE" | "TOGGLE" | "RADIO" | "MENU" | "DATE" | "BUTTON" | "UNKNOWN";
  current: string | number | boolean | null;
  choices: string[] | null;
  range: { min: number; max: number; step: number } | null;
}

export interface FocusNudgeRequest {
  step_size: number;
}

export type CaptureResult = components["schemas"]["CaptureResult"];
export type Angles = components["schemas"]["Angles"];
export type Configuration = components["schemas"]["Configuration"];
export type JobProgress = components["schemas"]["JobProgress"];
export type Job = components["schemas"]["Job"];
export type Session = components["schemas"]["Session"];
export type SessionSummary = components["schemas"]["SessionSummary"];
export type SessionAsset = components["schemas"]["SessionAsset"];
export type ApiErrorPayload = components["schemas"]["Error"];
