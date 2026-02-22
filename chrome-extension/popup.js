/**
 * Voice Bridge - Popup Script
 *
 * ポップアップ UI のイベントハンドリングと表示更新。
 * Processor ウィンドウからのメッセージを受信して表示する。
 */

// --- DOM 要素 ---

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const englishBox = document.getElementById("english-box");
const englishInterim = document.getElementById("english-interim");
const japaneseBox = document.getElementById("japanese-box");
const latencyText = document.getElementById("latency-text");
const offsetText = document.getElementById("offset-text");
const voiceSection = document.getElementById("voice-section");
const voiceSelect = document.getElementById("voice-select");
const tabVolume = document.getElementById("tab-volume");
const tabVolumeValue = document.getElementById("tab-volume-value");
const ttsRate = document.getElementById("tts-rate");
const ttsRateValue = document.getElementById("tts-rate-value");
const ttsVolume = document.getElementById("tts-volume");
const ttsVolumeValue = document.getElementById("tts-volume-value");

// --- 初期状態の復元 ---

chrome.runtime.sendMessage({ type: "POPUP_GET_STATE" }, (response) => {
  if (response && response.isCapturing) {
    setCapturingState(true);
  }
  if (response && response.voicevoxInfo && response.voicevoxInfo.available) {
    populateVoiceSelect(response.voicevoxInfo.speakers);
  }
});

// --- ボタンイベント ---

btnStart.addEventListener("click", () => {
  btnStart.disabled = true;
  statusText.textContent = "開始中...";

  chrome.runtime.sendMessage({ type: "POPUP_START" }, (response) => {
    if (response && response.success) {
      setCapturingState(true);
    } else {
      const errMsg = response?.error || "不明なエラー";
      statusText.textContent = `エラー: ${errMsg}`;
      btnStart.disabled = false;
    }
  });
});

btnStop.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "POPUP_STOP" }, () => {
    setCapturingState(false);
    latencyText.textContent = "翻訳: --";
    offsetText.textContent = "読んでる場所: --秒前";
  });
});

// --- 設定スライダー ---

tabVolume.addEventListener("input", () => {
  const val = parseFloat(tabVolume.value);
  tabVolumeValue.textContent = `${Math.round(val * 100)}%`;
  chrome.runtime.sendMessage({
    type: "UPDATE_CONFIG",
    tabVolume: val,
  });
});

ttsRate.addEventListener("input", () => {
  const val = parseFloat(ttsRate.value);
  ttsRateValue.textContent = `${val.toFixed(1)}x`;
  chrome.runtime.sendMessage({
    type: "UPDATE_CONFIG",
    ttsRate: val,
  });
});

ttsVolume.addEventListener("input", () => {
  const val = parseFloat(ttsVolume.value);
  ttsVolumeValue.textContent = `${Math.round(val * 100)}%`;
  chrome.runtime.sendMessage({
    type: "UPDATE_CONFIG",
    ttsVolume: val,
  });
});

// --- メッセージ受信 ---

chrome.runtime.onMessage.addListener((message) => {
  switch (message.type) {
    case "RECOGNITION_RESULT":
      if (message.isFinal) {
        addEntry(englishBox, message.text);
        englishInterim.textContent = "";
      } else {
        englishInterim.textContent = message.text;
      }
      break;

    case "TRANSLATION_RESULT":
      addEntry(japaneseBox, message.japanese);
      if (message.latency) {
        latencyText.textContent = `翻訳: ${message.latency}s`;
      }
      if (message.speechOffset) {
        offsetText.textContent = `${message.speechOffset}秒前の内容`;
      }
      break;

    case "TTS_OFFSET_UPDATE":
      // TTS再生完了時の発話からの全体オフセット
      if (message.endToEndOffset) {
        offsetText.textContent = `${message.endToEndOffset}秒前の内容`;
      }
      break;

    case "STATUS_UPDATE":
      statusText.textContent = message.status;
      break;

    case "PROCESSOR_STARTED":
      // VOICEVOX 話者リストを受信
      if (message.voicevoxAvailable && message.voicevoxSpeakers) {
        populateVoiceSelect(message.voicevoxSpeakers);
      }
      break;

    case "CREDIT_UPDATE":
      // VOICEVOX 利用表記を更新
      if (message.credit) {
        const creditEl = document.getElementById("credit-text");
        creditEl.textContent = `${message.credit} | 翻訳: Google Translate`;
      }
      break;
  }
});

// --- ヘルパー関数 ---

function setCapturingState(capturing) {
  btnStart.disabled = capturing;
  btnStop.disabled = !capturing;
  statusDot.className = `status-dot ${capturing ? "active" : "inactive"}`;
  statusText.textContent = capturing ? "キャプチャ中..." : "待機中";
}

let voiceSelectInitialized = false;

function populateVoiceSelect(speakers) {
  if (!speakers || speakers.length === 0) return;

  voiceSelect.innerHTML = "";
  let defaultFound = false;
  for (const name of speakers) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    if (!defaultFound && name.includes("ずんだもん") && name.includes("ノーマル")) {
      opt.selected = true;
      defaultFound = true;
    }
    voiceSelect.appendChild(opt);
  }
  voiceSection.style.display = "flex";

  // VOICEVOX クレジット表示
  const creditEl = document.getElementById("credit-text");
  const selectedName = voiceSelect.value.split("（")[0];
  creditEl.textContent = `VOICEVOX:${selectedName} | 翻訳: Google Translate`;

  // イベントリスナー（重複防止）
  if (!voiceSelectInitialized) {
    voiceSelectInitialized = true;
    voiceSelect.addEventListener("change", () => {
      chrome.runtime.sendMessage({
        type: "CHANGE_VOICE",
        voiceName: voiceSelect.value,
      });
      // クレジット更新
      const charName = voiceSelect.value.split("（")[0];
      creditEl.textContent = `VOICEVOX:${charName} | 翻訳: Google Translate`;
    });
  }
}

function addEntry(container, text) {
  const entry = document.createElement("div");
  entry.className = "entry";
  entry.textContent = text;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;

  const entries = container.querySelectorAll(".entry");
  if (entries.length > 20) {
    entries[0].remove();
  }
}
