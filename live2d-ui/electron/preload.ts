// Context-isolated preload. 現時点では API を公開しないが、
// 将来的にネイティブ機能を React 側へ橋渡しする場合のフックを残す。
import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("voiceBridge", {
  version: "0.1.0",
});
