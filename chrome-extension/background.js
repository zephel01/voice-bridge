/**
 * Voice Bridge - Service Worker (Background Script)
 *
 * Offscreen Document では SpeechRecognition の権限が得られないため、
 * 通常の拡張ページ（processor.html）を小さなウィンドウとして開き、
 * そこで音声処理を行う。
 */

let isCapturing = false;
let processorWindowId = null;
let voicevoxInfo = { available: false, speakers: [] };

// --- プロセッサウィンドウ管理 ---

async function openProcessorWindow(streamId) {
  // 既存のウィンドウがあれば閉じる
  await closeProcessorWindow();

  const url = chrome.runtime.getURL(
    `processor.html?streamId=${encodeURIComponent(streamId)}`
  );

  const win = await chrome.windows.create({
    url: url,
    type: "popup",
    width: 420,
    height: 260,
    top: 60,
    left: 60,
    focused: false,
  });

  processorWindowId = win.id;
}

async function closeProcessorWindow() {
  if (processorWindowId !== null) {
    try {
      await chrome.windows.remove(processorWindowId);
    } catch (e) {
      // すでに閉じられている
    }
    processorWindowId = null;
  }
}

// ウィンドウが閉じられたときの検知
chrome.windows.onRemoved.addListener((windowId) => {
  if (windowId === processorWindowId) {
    processorWindowId = null;
    isCapturing = false;
  }
});

// --- タブキャプチャ ---

async function startCapture(tabId) {
  const streamId = await chrome.tabCapture.getMediaStreamId({
    targetTabId: tabId,
  });

  await openProcessorWindow(streamId);
  isCapturing = true;
}

async function stopCapture() {
  chrome.runtime.sendMessage({ type: "STOP_CAPTURE" });
  isCapturing = false;
}

// --- メッセージハンドリング ---

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case "POPUP_START":
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          startCapture(tabs[0].id)
            .then(() => sendResponse({ success: true }))
            .catch((err) => sendResponse({ success: false, error: err.message }));
        } else {
          sendResponse({ success: false, error: "アクティブなタブが見つかりません" });
        }
      });
      return true;

    case "POPUP_STOP":
      stopCapture()
        .then(() => sendResponse({ success: true }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;

    case "POPUP_GET_STATE":
      sendResponse({ isCapturing, voicevoxInfo });
      return false;

    case "PROCESSOR_STARTED":
      isCapturing = true;
      if (message.voicevoxAvailable) {
        voicevoxInfo = {
          available: true,
          speakers: message.voicevoxSpeakers || [],
          speakerMap: message.voicevoxSpeakerMap || {},
        };
      }
      break;

    case "PROCESSOR_STOPPED":
      isCapturing = false;
      processorWindowId = null;
      break;
  }
});
