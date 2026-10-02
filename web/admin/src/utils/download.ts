/** 下载工具：将 fetch Response 落盘为浏览器下载文件 */

/** 从 Content-Disposition 解析文件名（兼容 filename / filename*=UTF-8'' 两种形式） */
function resolveFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const star = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (star) {
    try {
      return decodeURIComponent(star[1].trim())
    } catch {
      /* 解码失败走 fallback */
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain ? plain[1].trim() : fallback
}

/** 将 Response 转为 Blob 并触发浏览器下载（自动识别服务端文件名） */
export async function downloadResponseBlob(response: Response, fallbackFilename: string): Promise<void> {
  const blob = await response.blob()
  const filename = resolveFilename(response.headers.get('Content-Disposition'), fallbackFilename)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
