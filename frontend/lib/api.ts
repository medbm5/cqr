/**
 * Typed client for the Django API.
 *
 * The frontend never computes risk figures: it renders what `risk_engine`
 * produced. Every response type declared here mirrors a serializer on the API
 * side, so a modeling change surfaces as a type error rather than a blank chart.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly path: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      path,
    );
  }

  return (await response.json()) as T;
}

export interface HealthResponse {
  status: string;
  engine_version: string;
}

export const api = {
  health: () => request<HealthResponse>("/api/health/"),
};

export { API_URL };
