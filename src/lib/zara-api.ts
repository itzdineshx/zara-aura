/**
 * ZARA Home Automation API Client
 * Comprehensive interface to backend services for voice, chat, home automation, and real-time features.
 */

import type { ResponseMode } from "@/lib/settings";

export type BackendEmotion = "happy" | "angry" | "calm" | "neutral";
export type HomeAction =
  | "light_on"
  | "light_off"
  | "fan_on"
  | "fan_off"
  | "fan_speed_up"
  | "fan_speed_down"
  | "ac_on"
  | "ac_off"
  | "ac_temp_up"
  | "ac_temp_down"
  | "tv_on"
  | "tv_off"
  | "curtain_open"
  | "curtain_close"
  | "door_lock"
  | "door_unlock"
  | "all_on"
  | "all_off"
  | "scene_good_morning"
  | "scene_good_night"
  | "scene_away"
  | "scene_home"
  | "status_check";

export interface AudioFeatures {
  volume: number;
  pitch: number;
}

export interface BackendAction {
  [key: string]: string | number | boolean | null;
}

export interface ChatApiResponse {
  text: string;
  language: string;
  emotion: BackendEmotion;
  audio_features: AudioFeatures;
  action: BackendAction | null;
}

export interface VoiceApiResponse extends ChatApiResponse {
  transcript: string;
}

export interface HomeStatusResponse {
  connected: boolean;
  broker: string;
  control_topic: string;
  status_topic: string;
  last_status: Record<string, unknown> | null;
  last_status_at: string | null;
}

export interface HomeActionResponse {
  type: string;
  domain: string;
  status: "executed" | "failed" | "blocked_home_mode";
  action?: string;
  value?: number | string;
  target?: string;
  topic?: string;
  connected?: boolean;
  error?: string;
  detail?: string;
}

export interface HealthResponse {
  status: string;
}

export interface AudioFeaturesMessage {
  type: "audio_features";
  data: {
    volume: number;
    pitch: number;
    timestamp: number;
  };
}

export interface StreamConnectionMessage {
  type: "connection";
  data: {
    status: "connected" | "disconnected";
    timestamp: number;
  };
}

export type StreamMessage = AudioFeaturesMessage | StreamConnectionMessage | { type: string; data: unknown };

const BACKEND_BASE_URL = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

function endpoint(path: string): string {
  return `${BACKEND_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload?.detail) {
      return payload.detail;
    }
  } catch {
    // Fall through to status text.
  }

  return response.statusText || "Request failed";
}

async function requestJson<T>(urlPath: string, init: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(endpoint(urlPath), init);
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Unable to reach backend");
  }

  if (!response.ok) {
    const message = await parseError(response);
    throw new Error(message);
  }

  return (await response.json()) as T;
}

async function requestBlob(urlPath: string, init: RequestInit): Promise<Blob> {
  let response: Response;

  try {
    response = await fetch(endpoint(urlPath), init);
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Unable to reach backend");
  }

  if (!response.ok) {
    const message = await parseError(response);
    throw new Error(message);
  }

  return response.blob();
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health", {
    method: "GET",
  });
}

/**
 * Get current response mode
 */
export async function getMode(): Promise<{ mode: ResponseMode }> {
  return requestJson<{ mode: ResponseMode }>("/mode", {
    method: "GET",
  });
}

/**
 * Set response mode (online, smart, offline)
 */
export async function setMode(mode: ResponseMode): Promise<void> {
  await requestJson<{ mode: ResponseMode }>("/mode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ mode }),
  });
}

/**
 * Enable/disable home automation
 */
export async function setHomeAutomationEnabled(enabled: boolean): Promise<void> {
  await requestJson<{ enabled: boolean }>("/home-mode", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ enabled }),
  });
}

/**
 * Get home automation status
 */
export async function getHomeAutomationStatus(): Promise<{ enabled: boolean }> {
  return requestJson<{ enabled: boolean }>("/home-mode", {
    method: "GET",
  });
}

/**
 * Get MQTT home automation status and connectivity
 */
export async function getHomeStatus(): Promise<HomeStatusResponse> {
  return requestJson<HomeStatusResponse>("/home/status", {
    method: "GET",
  });
}

/**
 * Send voice audio for transcription and AI processing
 */
export async function processVoice(
  audioChunk: Blob,
  mode: ResponseMode,
  preferredLanguage?: string,
): Promise<VoiceApiResponse> {
  const formData = new FormData();
  formData.append("file", audioChunk, `zara-voice-${Date.now()}.webm`);
  formData.append("mode", mode);
  formData.append("synthesize", "false");
  if (preferredLanguage) {
    formData.append("preferred_language", preferredLanguage);
  }

  return requestJson<VoiceApiResponse>("/voice", {
    method: "POST",
    body: formData,
  });
}

/**
 * Send chat message for AI processing
 */
export async function sendChat(
  text: string,
  mode: ResponseMode,
  volume?: number,
  preferredLanguage?: string,
): Promise<ChatApiResponse> {
  return requestJson<ChatApiResponse>("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      mode,
      volume: volume ?? 0,
      preferred_language: preferredLanguage,
      synthesize: false,
    }),
  });
}

/**
 * Generate speech audio from text
 */
export async function generateSpeech(text: string, language?: string): Promise<Blob> {
  return requestBlob("/tts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      language,
    }),
  });
}

/**
 * Execute home automation action
 */
export async function executeHomeAction(action: HomeAction): Promise<HomeActionResponse> {
  return requestJson<HomeActionResponse>("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text: action,
      mode: "smart",
      synthesize: false,
    }),
  });
}

/**
 * Connect to WebSocket stream for real-time audio features
 * Yields audio features (volume, pitch) as they arrive
 */
export async function* streamAudioFeatures(): AsyncGenerator<AudioFeaturesMessage, void, unknown> {
  const ws = new WebSocket(`${BACKEND_BASE_URL.replace(/^http/, "ws")}/ws/orb`);

  try {
    await new Promise<void>((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = (event) => reject(new Error(`WebSocket error: ${event.type}`));
      ws.onclose = () => reject(new Error("WebSocket closed"));
    });

    // Connected
    yield {
      type: "connection",
      data: {
        status: "connected",
        timestamp: Date.now(),
      },
    } as StreamConnectionMessage;

    // Stream audio features
    while (ws.readyState === WebSocket.OPEN) {
      const message = await new Promise<MessageEvent>((resolve, reject) => {
        ws.onmessage = resolve;
        ws.onerror = (event) => reject(new Error(`WebSocket error: ${event.type}`));
        ws.onclose = () => reject(new Error("WebSocket closed"));
      });

      try {
        const data = JSON.parse(message.data as string) as AudioFeaturesMessage;
        if (data.type === "audio_features") {
          yield data;
        }
      } catch {
        // Ignore parse errors
      }
    }
  } finally {
    // Disconnected
    yield {
      type: "connection",
      data: {
        status: "disconnected",
        timestamp: Date.now(),
      },
    } as StreamConnectionMessage;

    if (ws.readyState !== WebSocket.CLOSED) {
      ws.close();
    }
  }
}

/**
 * Helper: Get audio blob URL for playback
 */
export function createAudioBlobUrl(blob: Blob): string {
  return URL.createObjectURL(blob);
}

/**
 * Helper: Revoke audio blob URL to free memory
 */
export function revokeAudioBlobUrl(url: string): void {
  URL.revokeObjectURL(url);
}

/**
 * Helper: Play audio blob
 */
export async function playAudio(blob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = createAudioBlobUrl(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      revokeAudioBlobUrl(url);
      resolve();
    };
    audio.onerror = (error) => {
      revokeAudioBlobUrl(url);
      reject(error);
    };
    audio.play().catch(reject);
  });
}
