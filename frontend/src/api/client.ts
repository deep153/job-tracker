export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
  }
}

const UNREACHABLE = "Can't reach the Job Tracker server. Make sure the backend is running.";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(UNREACHABLE, null);
  }
  // The dev server's proxy answers 502-504 when the backend isn't running.
  if ([502, 503, 504].includes(response.status)) {
    throw new ApiError(UNREACHABLE, response.status);
  }
  if (!response.ok) {
    if (response.status >= 500) {
      throw new ApiError(
        "The Job Tracker server ran into a problem. Check the backend logs and try again.",
        response.status,
      );
    }
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new ApiError(errorDetail(body?.detail) ?? `Request failed (${response.status}).`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** FastAPI sends a string for our own errors and a list of field errors for request validation. */
function errorDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
    return (detail[0].msg as string).replace(/^Value error, /, "");
  }
  return null;
}

export function sendJson(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}
