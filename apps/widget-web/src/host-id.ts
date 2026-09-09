const HOST_ID_PATTERN = /^AMULAI-HOST-[0-9a-f]{8}$/

export function resolveHostId(documentValue: Document, pathname: string): string | null {
  const metaHostId = documentValue
    .querySelector<HTMLMetaElement>('meta[name="amul-widget-host-id"]')
    ?.content.trim()
  if (metaHostId && HOST_ID_PATTERN.test(metaHostId)) return metaHostId

  const pathHostId = pathname.match(/^\/embed\/([^/]+)\/?$/)?.[1]
  if (!pathHostId) return null
  const decoded = decodeURIComponent(pathHostId)
  return HOST_ID_PATTERN.test(decoded) ? decoded : null
}
