/**
 * Common error handling & detail formatter for Torii frontend API calls.
 * Safely handles string error details, FastAPI 422 field error arrays,
 * generic JavaScript Error objects, and unknown caught exceptions.
 */

export function formatApiDetail(detail: unknown): string {
  if (!detail) return "An unexpected error occurred.";
  if (typeof detail === "string") {
    // If the string is serialized JSON, attempt to parse it
    if (detail.startsWith("[") || detail.startsWith("{")) {
      try {
        const parsed = JSON.parse(detail);
        return formatApiDetail(parsed);
      } catch {
        // Fallthrough if not valid JSON
      }
    }
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const locArr = Array.isArray((item as Record<string, unknown>).loc)
            ? ((item as Record<string, unknown>).loc as unknown[])
            : [];
          const loc = locArr.filter((l) => l !== "body" && l !== "query").join(" → ");
          const msg = String((item as Record<string, unknown>).msg || JSON.stringify(item));
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join(" | ");
  }

  if (typeof detail === "object") {
    const msg = (detail as Record<string, unknown>).msg || (detail as Record<string, unknown>).message;
    if (typeof msg === "string") return msg;
    return JSON.stringify(detail);
  }

  return String(detail);
}

export function formatErrorMessage(err: unknown): string {
  if (!err) return "An error occurred.";
  if (err instanceof Error) {
    return formatApiDetail(err.message);
  }
  return formatApiDetail(err);
}
