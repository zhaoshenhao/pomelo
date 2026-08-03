const levels = { debug: 0, info: 1, warn: 2, error: 3 }

function getLevel() {
  if (typeof process !== "undefined" && process.env?.NODE_ENV === "production") {
    return levels.info
  }
  return levels.debug
}

function formatLog(level, module, message, extra) {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    module,
    message,
    ...(extra || {}),
  }
  return JSON.stringify(entry)
}

const currentLevel = getLevel()

export const logger = {
  debug(module, message, extra) {
    if (currentLevel > levels.debug) return
    console.debug(formatLog("debug", module, message, extra))
  },
  info(module, message, extra) {
    if (currentLevel > levels.info) return
    console.info(formatLog("info", module, message, extra))
  },
  warn(module, message, extra) {
    if (currentLevel > levels.warn) return
    console.warn(formatLog("warn", module, message, extra))
  },
  error(module, message, extra) {
    console.error(formatLog("error", module, message, extra))
  },
}
