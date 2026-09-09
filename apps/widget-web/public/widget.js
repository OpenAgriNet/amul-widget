(() => {
  "use strict"

  const script = document.currentScript
  if (!(script instanceof HTMLScriptElement)) return

  const hostId = script.dataset.hostId ?? ""
  if (!/^AMULAI-HOST-[0-9a-f]{8}$/.test(hostId)) {
    console.error("Amul AI widget: invalid or missing data-host-id")
    return
  }

  const scriptUrl = new URL(script.src)
  const widgetOrigin = scriptUrl.origin
  const elementId = `amul-ai-widget-${hostId}`
  if (document.getElementById(elementId)) return

  const host = document.createElement("div")
  host.id = elementId
  host.dataset.open = "false"
  const root = host.attachShadow({ mode: "open" })

  const stylesheet = document.createElement("link")
  stylesheet.rel = "stylesheet"
  stylesheet.href = `${widgetOrigin}/widget-loader.css`

  const panel = document.createElement("div")
  panel.className = "amul-widget-panel"

  const frame = document.createElement("iframe")
  frame.title = "Amul AI assistant"
  frame.loading = "lazy"
  frame.allow = "microphone"
  frame.referrerPolicy = "no-referrer"
  frame.setAttribute("sandbox", "allow-scripts allow-same-origin")

  const launcher = document.createElement("button")
  launcher.type = "button"
  launcher.className = "amul-widget-launcher"
  launcher.setAttribute("aria-label", "Open Amul AI assistant")
  launcher.setAttribute("aria-expanded", "false")

  const logo = document.createElement("img")
  logo.src = `${widgetOrigin}/AmulLogo.svg`
  logo.alt = ""
  logo.width = 40
  logo.height = 40
  launcher.append(logo)
  panel.append(frame)
  root.append(stylesheet, panel, launcher)
  document.body.append(host)

  const setOpen = (open) => {
    if (open && !frame.src) {
      frame.src = `${widgetOrigin}/embed/${encodeURIComponent(hostId)}`
    }
    host.dataset.open = String(open)
    launcher.setAttribute("aria-expanded", String(open))
    launcher.setAttribute(
      "aria-label",
      open ? "Close Amul AI assistant" : "Open Amul AI assistant",
    )
  }

  launcher.addEventListener("click", () => setOpen(host.dataset.open !== "true"))
  window.addEventListener("message", (event) => {
    if (
      event.origin === widgetOrigin &&
      event.source === frame.contentWindow &&
      event.data?.type === "amul-widget:close" &&
      event.data?.hostId === hostId
    ) {
      setOpen(false)
    }
  })
})()
