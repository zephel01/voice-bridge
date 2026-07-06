import { app, BrowserWindow, shell } from "electron";
import path from "node:path";

const isDev = process.env.NODE_ENV === "development";

const DEV_SERVER_URL = "http://localhost:5173";

/**
 * shell.openExternal に渡す前に URL スキームを検証する。
 * http/https 以外（file:, javascript:, data: 等）は拒否する。
 */
function isAllowedExternalUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * webContents 内でのナビゲーション先を検証する。
 * 開発時は Vite dev server (http://localhost:5173) への遷移のみ許可し、
 * 本番時は file:// プロトコル（アプリ同梱の index.html 等）のみ許可する。
 */
function isAllowedNavigationUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (isDev) {
      return url.startsWith(DEV_SERVER_URL);
    }
    return parsed.protocol === "file:";
  } catch {
    return false;
  }
}

function createWindow(): void {
  const win = new BrowserWindow({
    width: 520,
    height: 760,
    frame: true,
    transparent: false,
    backgroundColor: "#0a0a0f",
    title: "Voice Bridge × Live2D",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedExternalUrl(url)) {
      shell.openExternal(url);
    } else {
      console.warn("[main] blocked window.open for disallowed URL:", url);
    }
    return { action: "deny" };
  });

  win.webContents.on("will-navigate", (event, url) => {
    if (!isAllowedNavigationUrl(url)) {
      console.warn("[main] blocked navigation to disallowed URL:", url);
      event.preventDefault();
    }
  });

  if (isDev) {
    win.loadURL(`${DEV_SERVER_URL}/`);
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
