import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Languages, LoaderCircle, Send, X } from "lucide-react"

import type {
  AnonymousSessionResponse,
  ChatStreamEvent,
  PublicHostConfig,
  WidgetLocale,
} from "@openagrinet/amul-widget-contracts"
import { getHostConfig, startAnonymousSession, streamChat, WidgetApiError } from "@/api"
import { Button } from "@/components/ui/button"
import { Field, FieldGroup } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { languageLabels, widgetCopy } from "@/copy"
import { resolveHostId } from "@/host-id"

type ChatMessage = {
  id: string
  role: "user" | "assistant"
  text: string
}

const hostId = resolveHostId(document, window.location.pathname)

function closeWidget(): void {
  if (window.parent !== window) {
    window.parent.postMessage({ type: "amul-widget:close", hostId }, "*")
  }
}

function App() {
  const [config, setConfig] = useState<PublicHostConfig | null>(null)
  const [session, setSession] = useState<AnonymousSessionResponse | null>(null)
  const [locale, setLocale] = useState<WidgetLocale>("gu")
  const [draft, setDraft] = useState("")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<"loading" | "ready" | "sending" | "error">(
    hostId ? "loading" : "error",
  )

  const copy = widgetCopy[locale]
  const enabledLocales = useMemo(
    () => config?.locales ?? (["en", "hi", "gu"] satisfies WidgetLocale[]),
    [config],
  )

  useEffect(() => {
    if (!hostId) return
    const controller = new AbortController()
    void (async () => {
      try {
        const hostConfig = await getHostConfig(hostId, controller.signal)
        setConfig(hostConfig)
        setLocale(hostConfig.default_locale)
        const anonymousSession = await startAnonymousSession(
          hostId,
          hostConfig.default_locale,
          controller.signal,
        )
        setSession(anonymousSession)
        setStatus("ready")
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setStatus("error")
        }
      }
    })()
    return () => controller.abort()
  }, [])

  const sendQuestion = async (question: string) => {
    const text = question.trim()
    if (!text || !session || status === "sending") return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text,
    }
    const assistantId = crypto.randomUUID()
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", text: "" },
    ])
    setDraft("")
    setStatus("sending")

    try {
      await streamChat(
        {
          conversation_id: session.session_id,
          message_id: assistantId,
          text,
          locale,
        },
        session.access_token,
        (event: ChatStreamEvent) => {
          if (event.event === "message.delta") {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, text: message.text + event.data.text }
                  : message,
              ),
            )
          }
          if (event.event === "error") throw new WidgetApiError(event.data)
        },
      )
      setStatus("ready")
    } catch {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, text: copy.unavailable } : message,
        ),
      )
      setStatus("error")
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void sendQuestion(draft)
  }

  return (
    <div className="widget-surface flex h-svh w-full flex-col overflow-hidden text-foreground">
      <header className="flex items-center justify-between p-3">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="icon-sm" aria-label={copy.language}>
              <Languages />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-auto">
            <ToggleGroup
              type="single"
              orientation="vertical"
              value={locale}
              onValueChange={(value) => {
                if (value) setLocale(value as WidgetLocale)
              }}
            >
              {enabledLocales.map((code) => (
                <ToggleGroupItem key={code} value={code} aria-label={languageLabels[code]}>
                  {languageLabels[code]}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </PopoverContent>
        </Popover>

        <Button variant="ghost" size="icon-sm" onClick={closeWidget} aria-label={copy.close}>
          <X />
        </Button>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto px-4">
        {status === "error" && !session ? (
          <section className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <img src="/AmulLogo.svg" alt="" className="size-16" />
            <p className="max-w-xs text-sm text-muted-foreground">{copy.unavailable}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              {copy.retry}
            </Button>
          </section>
        ) : messages.length === 0 ? (
          <section className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <img src="/AmulLogo.svg" alt="" className="size-16" />
            <div className="flex w-full max-w-sm flex-col gap-1.5">
              <h1 className="text-lg font-semibold">Amul AI</h1>
              <p className="text-xs leading-relaxed text-muted-foreground">{copy.welcome}</p>
            </div>
          </section>
        ) : (
          <ol className="mx-auto flex max-w-xl flex-col gap-3 py-4" aria-live="polite">
            {messages.map((message) => (
              <li
                key={message.id}
                data-role={message.role}
                className="widget-message max-w-[85%] rounded-2xl px-3 py-2 text-sm"
              >
                {message.text || <LoaderCircle className="animate-spin" aria-label="Loading" />}
              </li>
            ))}
          </ol>
        )}
      </main>

      <footer className="flex flex-col gap-3 border-t bg-card p-3">
        <div className="scrollbar-none flex gap-2 overflow-x-auto">
          {copy.questions.map((question) => (
            <Button
              key={question}
              variant="outline"
              size="sm"
              onClick={() => void sendQuestion(question)}
              disabled={!session || status === "sending"}
            >
              {question}
            </Button>
          ))}
        </div>

        <form onSubmit={submit}>
          <FieldGroup>
            <Field>
              <InputGroup className="h-11 rounded-full">
                <InputGroupInput
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={copy.placeholder}
                  aria-label={copy.placeholder}
                  disabled={!session || status === "sending"}
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    type="submit"
                    size="icon-sm"
                    variant="default"
                    aria-label={copy.send}
                    disabled={!draft.trim() || !session || status === "sending"}
                  >
                    {status === "sending" ? <LoaderCircle className="animate-spin" /> : <Send />}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
            </Field>
          </FieldGroup>
        </form>
      </footer>
    </div>
  )
}

export default App
