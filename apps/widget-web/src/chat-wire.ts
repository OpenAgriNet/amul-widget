// The advisory API streams plain text and appends framed metadata to it (amul-oan-api
// app/chat_artifacts.py). amul-ui parses these frames out in src/lib/chat-artifacts.ts; the
// widget shows none of them, so it only cuts them out of the text. Artifacts and milk-collection
// payloads need a signed-in farmer today, so an anonymous widget session should not receive
// them, but a frame must never reach the farmer as raw base64 if one does.
const FRAMES = [
  { start: "\n__CHAT_ARTIFACTS__", end: "__END_CHAT_ARTIFACTS__\n" },
  { start: "__SUGGESTIONS__", end: "__END_SUGGESTIONS__" },
]

// Backend guardrail prefixes milk-collection payloads with a success line (amul-ui strips it too).
const MILK_COLLECTION_PREFIX = /^Farmer milk collection details fetched successfully:\s*\n*/i

/** Length of a frame start marker cut off at the end of the buffer by chunking. */
function partialMarkerLength(value: string): number {
  let held = 0
  for (const { start } of FRAMES) {
    for (let length = Math.min(value.length, start.length - 1); length > held; length--) {
      if (value.endsWith(start.slice(0, length))) {
        held = length
        break
      }
    }
  }
  return held
}

/** The answer text to show for the wire buffer received so far; safe across split frames. */
export function assistantDisplayText(wire: string): string {
  let text = ""
  let cursor = 0

  while (cursor < wire.length) {
    const next = FRAMES.map((frame) => ({ frame, at: wire.indexOf(frame.start, cursor) }))
      .filter(({ at }) => at >= 0)
      .sort((a, b) => a.at - b.at)[0]

    if (!next) {
      const rest = wire.slice(cursor)
      const held = partialMarkerLength(rest)
      text += held ? rest.slice(0, -held) : rest
      break
    }

    text += wire.slice(cursor, next.at)
    const end = wire.indexOf(next.frame.end, next.at + next.frame.start.length)
    // A frame still arriving is held back until its end marker lands.
    if (end < 0) break
    cursor = end + next.frame.end.length
  }

  return text.replace(MILK_COLLECTION_PREFIX, "")
}
