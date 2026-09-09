export const widgetLocales = ["en", "hi", "gu"] as const
export type WidgetLocale = (typeof widgetLocales)[number]

export type WidgetFeature = "advisory_chat" | "voice_input"

export type PublicHostConfig = {
  host_id: string
  partner_name: string
  features: WidgetFeature[]
  locales: WidgetLocale[]
  default_locale: WidgetLocale
}

export type AnonymousSessionRequest = {
  host_id: string
  locale: WidgetLocale
}

export type AnonymousSessionResponse = {
  session_id: string
  access_token: string
  token_type: "bearer"
  expires_in: number
  features: WidgetFeature[]
}

export type ChatStreamRequest = {
  conversation_id: string | null
  message_id: string
  text: string
  locale: WidgetLocale
}

export type ProblemDetails = {
  type: string
  title: string
  status: number
  code: string
  request_id: string
  detail?: string
  retry_after?: number
}

export type ChatStreamEvent =
  | {
      event: "turn.started"
      data: { conversation_id: string }
    }
  | {
      event: "message.delta"
      data: { text: string }
    }
  | {
      event: "message.completed"
      data: { conversation_id: string; message_id: string }
    }
  | {
      event: "error"
      data: ProblemDetails
    }
