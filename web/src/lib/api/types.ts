import type { components } from "./generated";

export type HardwareState = components["schemas"]["CameraStatus"]["state"];
export type CalibrationValue = components["schemas"]["HardwareStatus"]["calibration"]["state"];
export type JobStatus = components["schemas"]["Job"]["status"];
export type CameraStatus = components["schemas"]["CameraStatus"];
export type TripodStatus = components["schemas"]["TripodStatus"];
export type HardwareStatus = components["schemas"]["HardwareStatus"];
export type CameraSettings = components["schemas"]["CameraSettings"];
export type CaptureResult = components["schemas"]["CaptureResult"];
export type Angles = components["schemas"]["Angles"];
export type Configuration = components["schemas"]["Configuration"];
export type JobProgress = components["schemas"]["JobProgress"];
export type Job = components["schemas"]["Job"];
export type Session = components["schemas"]["Session"];
export type SessionSummary = components["schemas"]["SessionSummary"];
export type SessionAsset = components["schemas"]["SessionAsset"];
export type ApiErrorPayload = components["schemas"]["Error"];
