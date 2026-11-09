// The advisory API streams plain text and appends a framed artifact envelope to it (amul-oan-api
// app/chat_artifacts.py). amul-ui parses the frame out in src/lib/chat-artifacts.ts; the widget
// shows no artifacts, so it only cuts the frame out of the text. Artifacts and milk-collection
// payloads need a signed-in farmer today, so an anonymous widget session should not receive
// them, but a frame must never reach the farmer as raw base64 if one does.
//
// amul-ui also parses a `__SUGGESTIONS__` frame that the API does not emit. It is left out here:
// holding back a partial `__` marker would eat the closing `__` of an answer ending in bold.
const FRAME_START = "\n__CHAT_ARTIFACTS__"
const FRAME_END = "__END_CHAT_ARTIFACTS__\n"

// Backend guardrail prefixes milk-collection payloads with a success line (amul-ui strips it too).
const MILK_COLLECTION_PREFIX = /^Farmer milk collection details fetched successfully:\s*\n*/i

/** Length of a frame start marker cut off at the end of the buffer by chunking. */
function partialMarkerLength(value: string): number {
  for (let length = Math.min(value.length, FRAME_START.length - 1); length > 0; length--) {
    if (value.endsWith(FRAME_START.slice(0, length))) return length
  }
  return 0
}

/** The answer text to show for the wire buffer received so far; safe across split frames. */
export function assistantDisplayText(wire: string): string {
  let text = ""
  let cursor = 0

  while (cursor < wire.length) {
    const start = wire.indexOf(FRAME_START, cursor)
    if (start < 0) {
      const rest = wire.slice(cursor)
      const held = partialMarkerLength(rest)
      text += held ? rest.slice(0, -held) : rest
      break
    }

    text += wire.slice(cursor, start)
    const end = wire.indexOf(FRAME_END, start + FRAME_START.length)
    // A frame still arriving is held back until its end marker lands.
    if (end < 0) break
    cursor = end + FRAME_END.length
  }

  return text.replace(MILK_COLLECTION_PREFIX, "")
}
