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

    expect(html).toMatch(/<p[^>]*>ગાયો અને ભેંસમાં દૂધ ઉત્પાદન વધારવા માટે:<\/p>/)
    expect(html).toMatch(/<ul class="[^"]*list-disc/)
    expect(html).toMatch(/<strong[^>]*>સંતુલિત ચારો:<\/strong>/)
    expect(html).not.toContain("**")
    expect(html).not.toMatch(/(^|>)\s*\*\s/)
  })

  it("lets a two-column table fill the bubble", () => {
    const html = render("| પશુ | દાણા |\n| --- | --- |\n| ગાય | 400 ગ્રામ |")

    expect(html).toMatch(/<table[^>]*class="[^"]*w-full/)
    expect(html).not.toContain("sticky")
    expect(html).toContain("<div>400 ગ્રામ</div>")
  })

  it("scrolls a wider table inside the bubble with the first column pinned", () => {
    const html = render(
      "| ચીજવસ્તુ | બજાર | ભાવ |\n| :--- | :--- | :--- |\n| ટમેટા | હિંમતનગર | 850 |",
    )

    expect(html).toContain('class="overflow-x-auto overscroll-x-contain"')
    expect(html).toMatch(/<table[^>]*class="[^"]*w-max min-w-full/)
    expect(html).toContain("[&amp;_tr&gt;:first-child]:sticky")
    expect(html).toMatch(/<td[^>]*data-numeric="true"[^>]*><div>850<\/div><\/td>/)
  })

  it("escapes raw HTML", () => {
    expect(render('<img src="x" onerror="alert(1)">')).not.toContain("<img")
  })

  it("opens links outside the frame", () => {
    const html = render("[Amul](https://amul.com)")

    expect(html).toMatch(/<a href="https:\/\/amul.com"[^>]*target="_blank"[^>]*>Amul<\/a>/)
    expect(html).toContain('rel="noopener noreferrer"')
  })
})
