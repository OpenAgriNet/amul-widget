import type {
  AnonymousSessionResponse,
  ChatStreamEvent,
  ChatStreamRequest,
  ProblemDetails,
  PublicHostConfig,
  WidgetLocale,
} from "@openagrinet/amul-widget-contracts"

export class WidgetApiError extends Error {
  readonly problem: ProblemDetails

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title)
    this.name = "WidgetApiError"
    this.problem = problem
  }
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, { ...init, signal })
  if (!response.ok) {
    const problem = (await response.json()) as ProblemDetails
    throw new WidgetApiError(problem)
  }
  return (await response.json()) as T
}

export function getHostConfig(
  hostId: string,
  signal?: AbortSignal,
): Promise<PublicHostConfig> {
  return requestJson(`/api/v1/hosts/${encodeURIComponent(hostId)}/config`, undefined, signal)
}

export function startAnonymousSession(
  hostId: string,
  locale: WidgetLocale,
  signal?: AbortSignal,
): Promise<AnonymousSessionResponse> {
  return requestJson(
    "/api/v1/sessions/anonymous",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host_id: hostId, locale }),
    },
    signal,
  )
}

export function parseSseBlock(block: string): ChatStreamEvent | null {
  let eventName = ""
  const dataLines: string[] = []
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) eventName = line.slice(6).trim()
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart())
  }
  if (!eventName || dataLines.length === 0) return null
  return {
    event: eventName,
    data: JSON.parse(dataLines.join("\n")),
  } as ChatStreamEvent
}

export async function streamChat(
  payload: ChatStreamRequest,
  accessToken: string,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new WidgetApiError((await response.json()) as ProblemDetails)
  }
  if (!response.body) throw new Error("The advisory stream did not return a body")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() ?? ""
    for (const block of blocks) {
      const event = parseSseBlock(block)
      if (event) onEvent(event)
    }
    if (done) break
  }

  const finalEvent = parseSseBlock(buffer)
  if (finalEvent) onEvent(finalEvent)
}
