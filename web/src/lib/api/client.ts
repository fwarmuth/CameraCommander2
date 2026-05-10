import type {
  ApiErrorPayload,
  CameraSettings,
  CaptureResult,
  Configuration,
  HardwareStatus,
  Job,
  Session,
  SessionSummary,
  TripodStatus,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: ApiErrorPayload,
  ) {
    super(payload.message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const payload = (await response.json()) as ApiErrorPayload;
    throw new ApiError(response.status, payload);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: "ok"; version: string; uptime_s: number }>("/api/health"),
  hardwareStatus: () => request<HardwareStatus>("/api/hardware/status"),

  cameraSettings: () => request<CameraSettings>("/api/camera/settings"),
  updateCameraSettings: (settings: Record<string, string | number | boolean>) =>
    request<CameraSettings>("/api/camera/settings", {
      method: "PUT",
      body: JSON.stringify({ settings, step_policy: "strict" }),
    }),
  captureCamera: (autofocus = false) =>
    request<CaptureResult>("/api/camera/capture", {
      method: "POST",
      body: JSON.stringify({ autofocus }),
    }),

  tripodStatus: () => request<TripodStatus>("/api/tripod/status"),
  moveTripod: (pan: number, tilt: number) =>
    request<TripodStatus>("/api/tripod/move", {
      method: "POST",
      body: JSON.stringify({ pan_deg: pan, tilt_deg: tilt }),
    }),
  nudgeTripod: (deltaPan: number, deltaTilt: number) =>
    request<TripodStatus>("/api/tripod/nudge", {
      method: "POST",
      body: JSON.stringify({ delta_pan_deg: deltaPan, delta_tilt_deg: deltaTilt }),
    }),
  homeTripod: () => request<TripodStatus>("/api/tripod/home", { method: "POST" }),
  stopTripod: () => request<void>("/api/tripod/stop", { method: "POST" }),
  setTripodDrivers: (enabled: boolean) =>
    request<TripodStatus>("/api/tripod/drivers", {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }),

  launchTimelapse: (config: Configuration) =>
    request<Job>("/api/jobs/timelapse", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  launchVideoPan: (config: Configuration) =>
    request<Job>("/api/jobs/video-pan", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  activeJob: () => request<Job | null>("/api/jobs/active"),
  job: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),
  stopJob: (jobId: string) => request<Job>(`/api/jobs/${jobId}/stop`, { method: "POST" }),

  sessions: (params?: { limit?: number; offset?: number; tag?: string }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.tag) query.set("tag", params.tag);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<{ items: SessionSummary[]; total: number }>(`/api/sessions${suffix}`);
  },
  session: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}`),
  deleteSession: (sessionId: string) =>
    request<void>(`/api/sessions/${sessionId}`, { method: "DELETE" }),
  sessionConfig: (sessionId: string) =>
    request<Configuration>(`/api/sessions/${sessionId}/config`),
  assembleSession: (sessionId: string) =>
    request<Session>(`/api/sessions/${sessionId}/assemble`, { method: "POST" }),
};
