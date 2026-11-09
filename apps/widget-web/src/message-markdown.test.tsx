import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { MessageMarkdown } from "@/message-markdown"

const render = (text: string) => renderToStaticMarkup(<MessageMarkdown text={text} />)

describe("MessageMarkdown", () => {
  it("renders the advisory answer's bullets and bold labels instead of raw markers", () => {
    // Shape taken from a production widget answer (2026-11-09).
    const html = render(
      "ગાયો અને ભેંસમાં દૂધ ઉત્પાદન વધારવા માટે:\n\n" +
        "* **સંતુલિત ચારો:** અમૂલ કેટલ ફીડ જેવા પેલેટ ચારાનો ઉપયોગ કરો.\n" +
        "* **વિશિષ્ટ દાણાનો ઉપયોગ:**\n" +
        " * **અમૂલ બાયપાસ દાણા:** દિવસમાં 10 લિટરથી ઓછું દૂધ આપતા પશુઓ માટે.",
    )

    expect(html).toContain("<p>ગાયો અને ભેંસમાં દૂધ ઉત્પાદન વધારવા માટે:</p>")
    expect(html).toContain("<ul>")
    expect(html).toContain("<strong>સંતુલિત ચારો:</strong>")
    expect(html).not.toContain("**")
    expect(html).not.toMatch(/(^|>)\s*\*\s/)
  })

  it("renders tables", () => {
    const html = render("| પશુ | દાણા |\n| --- | --- |\n| ગાય | 400 ગ્રામ |")

    expect(html).toContain("<table>")
    expect(html).toContain("<td>400 ગ્રામ</td>")
  })

  it("escapes raw HTML", () => {
    const html = render('<img src="x" onerror="alert(1)">')

    expect(html).not.toContain("<img")
  })

  it("opens links outside the frame", () => {
    const html = render("[Amul](https://amul.com)")

    expect(html).toContain(
      '<a href="https://amul.com" target="_blank" rel="noopener noreferrer">Amul</a>',
    )
  })
})
