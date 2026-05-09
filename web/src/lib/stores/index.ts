import { writable } from "svelte/store";
export const hardwareStatus = writable({ camera: { state: "disconnected" }, tripod: { state: "disconnected" } });
export const activeJob = writable(null);
