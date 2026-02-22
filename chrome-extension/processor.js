/**
 * Voice Bridge - Processor Window
 *
 * 通常の拡張ページ（ウィンドウ）で音声処理を行う。
 * Offscreen Document と異なり、通常ページコンテキストなので
 * SpeechRecognition が正常に動作する。
 *
 * パイプライン:
 *   tabCapture → AudioContext + GainNode（元音声再生・音量調整）
 *              → SpeechRecognition（英語認識）
 *              → Google Translate（翻訳）
 *              → SpeechSynthesis（日本語読み上げ）
 */

// --- DOM ---
const statusText = document.getElementById("status-text");
const logEl = document.getElementById("log");

// --- 状態管理 ---
let mediaStream = null;
let audioContext = null;
let gainNode = null;
let recognition = null;
let translator = new Translator();
let isRunning = false;
let currentAudioTrack = null;

// VOICEVOX 状態
let voicevoxAvailable = false;
let voicevoxSpeakers = {};  // { "ずんだもん（ノーマル）": 3, ... }
let voicevoxSpeakerId = 3;  // デフォルト: ずんだもん

// 発話オフセット追跡
// interim結果が初めて出た時刻 = 実際の発話タイミングの近似値
let utteranceStartTime = null;

// 設定
const CONFIG = {
  recognitionLang: "en-US",
  ttsLang: "ja-JP",
  ttsRate: 0.9,
  ttsVolume: 1.0,
  tabVolume: 1.0,        // タブ音声のパススルー音量
  minTextLength: 3,
  voicevoxHost: "http://localhost:50021",
};

// --- URL パラメータからストリーム ID を取得 ---
const params = new URLSearchParams(window.location.search);
const streamId = params.get("streamId");

if (streamId) {
  startCapture(streamId);
} else {
  setStatus("エラー: streamId がありません");
}

// --- 音声キャプチャ ---

async function startCapture(streamId) {
  try {
    setStatus("タブ音声をキャプチャ中...");

    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: "tab",
          chromeMediaSourceId: streamId,
        },
      },
    });

    log("sys", "タブ音声キャプチャ成功");

    // タブの音声をパススルー再生（GainNode で音量調整可能に）
    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(mediaStream);
    gainNode = audioContext.createGain();
    gainNode.gain.value = CONFIG.tabVolume;
    source.connect(gainNode);
    gainNode.connect(audioContext.destination);

    log("sys", "音声パススルー開始（音量調整可能）");

    // AudioTrack を取得
    currentAudioTrack = mediaStream.getAudioTracks()[0];
    if (!currentAudioTrack) {
      throw new Error("音声トラックが取得できません");
    }

    // VOICEVOX 検出
    await detectVoicevox();

    // 音声認識を開始
    isRunning = true;
    startRecognition();

    setStatus("キャプチャ中...");

    // Service Worker に状態を通知（VOICEVOX 話者リスト + IDマップ付き）
    chrome.runtime.sendMessage({
      type: "PROCESSOR_STARTED",
      voicevoxAvailable: voicevoxAvailable,
      voicevoxSpeakers: Object.keys(voicevoxSpeakers),
      voicevoxSpeakerMap: voicevoxSpeakers,
    });

  } catch (err) {
    console.error("[Processor] キャプチャエラー:", err);
    setStatus(`エラー: ${err.message}`);
    log("sys", `エラー: ${err.message}`);
  }
}

// --- 音声認識 ---

function startRecognition() {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    setStatus("エラー: Web Speech API 非対応");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = CONFIG.recognitionLang;
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const text = result[0].transcript;

      if (result.isFinal) {
        const trimmed = text.trim();
        if (trimmed.length >= CONFIG.minTextLength) {
          const recognizedAt = Date.now();
          // 発話開始時刻: interimが最初に出た時刻（なければ認識確定時刻）
          const speechStartTime = utteranceStartTime || recognizedAt;
          utteranceStartTime = null; // リセット

          console.log(`[認識-確定] ${trimmed}`);
          log("en", trimmed);
          chrome.runtime.sendMessage({
            type: "RECOGNITION_RESULT",
            text: trimmed,
            isFinal: true,
          });
          // 翻訳を即座に開始（発話開始時刻付き）
          processTranslation(trimmed, recognizedAt, speechStartTime);
        }
      } else {
        // 最初のinterim結果で発話開始時刻を記録
        if (utteranceStartTime === null) {
          utteranceStartTime = Date.now();
        }
        chrome.runtime.sendMessage({
          type: "RECOGNITION_RESULT",
          text: text,
          isFinal: false,
        });
      }
    }
  };

  recognition.onerror = (event) => {
    console.warn("[Processor] 認識エラー:", event.error);
    if (event.error === "no-speech" || event.error === "aborted") {
      // 無音・明示的停止は無視
    } else {
      log("sys", `認識エラー: ${event.error}`);
    }
  };

  recognition.onend = () => {
    if (isRunning) {
      // 即座に再開（待ち時間なし）
      try {
        if (currentAudioTrack && currentAudioTrack.readyState === "live") {
          recognition.start(currentAudioTrack);
        } else {
          recognition.start();
        }
      } catch (e) {
        // 少しだけ待ってリトライ
        setTimeout(() => {
          if (!isRunning) return;
          try {
            if (currentAudioTrack && currentAudioTrack.readyState === "live") {
              recognition.start(currentAudioTrack);
            } else {
              recognition.start();
            }
          } catch (_) {}
        }, 100);
      }
    }
  };

  // 認識開始: まず AudioTrack を渡す方式を試す（Chrome 127+）
  // 失敗したら通常のマイク方式にフォールバック
  try {
    recognition.start(currentAudioTrack);
    log("sys", "音声認識開始（タブ音声モード）");
  } catch (e) {
    console.warn("[Processor] AudioTrack モード失敗、マイクモードで再試行:", e.message);
    try {
      recognition.start();
      log("sys", "音声認識開始（マイクモード）");
    } catch (e2) {
      setStatus(`認識開始エラー: ${e2.message}`);
      log("sys", `認識開始エラー: ${e2.message}`);
    }
  }
}

// --- 翻訳（非同期・読み上げと並行） ---

let ttsQueue = [];
let isSpeaking = false;

async function processTranslation(englishText, recognizedAt, speechStartTime) {
  setStatus("翻訳中...");

  try {
    const japaneseText = await translator.translate(englishText);
    const translateDoneAt = Date.now();
    const transLatency = ((translateDoneAt - recognizedAt) / 1000).toFixed(1);
    // 発話時点からの経過時間（認識遅延 + 翻訳遅延）
    const totalOffset = ((translateDoneAt - speechStartTime) / 1000).toFixed(1);

    if (japaneseText) {
      console.log(`[翻訳] ${englishText} → ${japaneseText} (翻訳${transLatency}s / 発話から${totalOffset}s)`);
      log("ja", `${japaneseText}  [${transLatency}s]`);

      // Popup に送信（翻訳遅延 + 発話オフセット付き）
      chrome.runtime.sendMessage({
        type: "TRANSLATION_RESULT",
        english: englishText,
        japanese: japaneseText,
        latency: transLatency,
        speechOffset: totalOffset,
        speechStartTime: speechStartTime,
      });

      // 読み上げキューに追加（発話開始時刻を添付してTTS完了後にも計測）
      enqueueTTS(japaneseText, speechStartTime);
    }
  } catch (err) {
    console.error("[Processor] 翻訳エラー:", err);
    log("sys", `翻訳エラー: ${err.message}`);
  }

  setStatus("キャプチャ中...");
}

// --- VOICEVOX ---

async function detectVoicevox() {
  try {
    const res = await fetch(`${CONFIG.voicevoxHost}/version`, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      const version = await res.text();
      log("sys", `VOICEVOX 検出 (v${version})`);
      voicevoxAvailable = true;

      // 話者リストを取得
      const speakersRes = await fetch(`${CONFIG.voicevoxHost}/speakers`);
      const speakers = await speakersRes.json();
      voicevoxSpeakers = {};
      for (const speaker of speakers) {
        for (const style of speaker.styles) {
          const key = `${speaker.name}（${style.name}）`;
          voicevoxSpeakers[key] = style.id;
        }
      }
      log("sys", `VOICEVOX: ${Object.keys(voicevoxSpeakers).length}話者`);
    }
  } catch (e) {
    voicevoxAvailable = false;
    log("sys", "VOICEVOX 未検出 → Web Speech Synthesis を使用");
  }
}

async function voicevoxSynthesize(text) {
  try {
    // 1. AudioQuery を作成
    const queryRes = await fetch(
      `${CONFIG.voicevoxHost}/audio_query?text=${encodeURIComponent(text)}&speaker=${voicevoxSpeakerId}`,
      { method: "POST" }
    );
    if (!queryRes.ok) throw new Error(`audio_query: ${queryRes.status}`);
    const query = await queryRes.json();

    // 速度を反映
    query.speedScale = CONFIG.ttsRate;
    query.volumeScale = CONFIG.ttsVolume;

    // 2. 音声合成
    const synthRes = await fetch(
      `${CONFIG.voicevoxHost}/synthesis?speaker=${voicevoxSpeakerId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(query),
      }
    );
    if (!synthRes.ok) throw new Error(`synthesis: ${synthRes.status}`);

    const wavBlob = await synthRes.blob();
    return URL.createObjectURL(wavBlob);
  } catch (e) {
    console.error("[VOICEVOX] 合成エラー:", e);
    return null;
  }
}

function playAudioUrl(url) {
  return new Promise((resolve) => {
    const audio = new Audio(url);
    audio.volume = CONFIG.ttsVolume;

    // タブ音量を下げる
    if (gainNode && audioContext) {
      gainNode.gain.setTargetAtTime(0.3, audioContext.currentTime, 0.1);
    }

    audio.onended = () => {
      URL.revokeObjectURL(url);
      if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(CONFIG.tabVolume, audioContext.currentTime, 0.1);
      }
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(CONFIG.tabVolume, audioContext.currentTime, 0.1);
      }
      resolve();
    };

    audio.play().catch(() => resolve());
  });
}

// --- TTS（キュー方式・翻訳と並行） ---

function enqueueTTS(text, speechStartTime) {
  ttsQueue.push({ text, speechStartTime });
  if (!isSpeaking) {
    processTTSQueue();
  }
}

async function processTTSQueue() {
  if (isSpeaking || ttsQueue.length === 0) return;
  isSpeaking = true;

  while (ttsQueue.length > 0) {
    const item = ttsQueue.shift();
    await speakJapanese(item.text);

    // TTS再生完了時点での発話からの全体オフセット
    if (item.speechStartTime) {
      const endToEndSec = ((Date.now() - item.speechStartTime) / 1000).toFixed(1);
      chrome.runtime.sendMessage({
        type: "TTS_OFFSET_UPDATE",
        endToEndOffset: endToEndSec,
      });
    }
  }

  isSpeaking = false;
}

async function speakJapanese(text) {
  // VOICEVOX が使えるならそちらを使用
  if (voicevoxAvailable) {
    const audioUrl = await voicevoxSynthesize(text);
    if (audioUrl) {
      await playAudioUrl(audioUrl);
      return;
    }
    // VOICEVOX 失敗 → Web Speech にフォールバック
    console.warn("[TTS] VOICEVOX 失敗、Web Speech にフォールバック");
  }

  // Web Speech Synthesis
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = CONFIG.ttsLang;
    utterance.rate = CONFIG.ttsRate;
    utterance.volume = CONFIG.ttsVolume;

    const voices = speechSynthesis.getVoices();
    const jaVoice =
      voices.find((v) => v.lang.startsWith("ja") && v.localService) ||
      voices.find((v) => v.lang.startsWith("ja"));
    if (jaVoice) {
      utterance.voice = jaVoice;
    }

    // タブ音声を少し下げて読み上げを聞きやすくする
    if (gainNode && audioContext) {
      gainNode.gain.setTargetAtTime(0.3, audioContext.currentTime, 0.1);
    }

    utterance.onend = () => {
      if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(CONFIG.tabVolume, audioContext.currentTime, 0.1);
      }
      resolve();
    };
    utterance.onerror = (e) => {
      console.warn("[TTS] エラー:", e.error);
      if (gainNode && audioContext) {
        gainNode.gain.setTargetAtTime(CONFIG.tabVolume, audioContext.currentTime, 0.1);
      }
      resolve();
    };

    speechSynthesis.speak(utterance);
  });
}

// 音声リスト読み込み
speechSynthesis.onvoiceschanged = () => {
  const jaVoices = speechSynthesis.getVoices().filter((v) => v.lang.startsWith("ja"));
  if (jaVoices.length > 0) {
    log("sys", `日本語音声: ${jaVoices.map((v) => v.name).join(", ")}`);
  }
};

// --- ヘルパー ---

function setStatus(text) {
  statusText.textContent = text;
  chrome.runtime.sendMessage({ type: "STATUS_UPDATE", status: text });
}

function log(type, text) {
  const div = document.createElement("div");
  div.className = type;
  div.textContent = type === "ja" ? `→ ${text}` : text;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;

  while (logEl.children.length > 50) {
    logEl.firstChild.remove();
  }
}

// --- メッセージ受信 ---

chrome.runtime.onMessage.addListener((message) => {
  switch (message.type) {
    case "STOP_CAPTURE":
      stopCapture();
      break;
    case "UPDATE_CONFIG":
      if (message.ttsRate !== undefined) CONFIG.ttsRate = message.ttsRate;
      if (message.ttsVolume !== undefined) CONFIG.ttsVolume = message.ttsVolume;
      if (message.tabVolume !== undefined) {
        CONFIG.tabVolume = message.tabVolume;
        if (gainNode && audioContext) {
          gainNode.gain.setTargetAtTime(CONFIG.tabVolume, audioContext.currentTime, 0.1);
        }
      }
      break;
    case "CHANGE_VOICE":
      if (message.voiceName && voicevoxSpeakers[message.voiceName] !== undefined) {
        voicevoxSpeakerId = voicevoxSpeakers[message.voiceName];
        const charName = message.voiceName.split("（")[0];
        log("sys", `話者変更: ${message.voiceName} (ID=${voicevoxSpeakerId})`);
        // VOICEVOX 利用表記を更新
        chrome.runtime.sendMessage({
          type: "CREDIT_UPDATE",
          credit: `VOICEVOX:${charName}`,
        });
      }
      break;
  }
});

function stopCapture() {
  isRunning = false;

  if (recognition) {
    recognition.abort();
    recognition = null;
  }
  if (audioContext) {
    audioContext.close().catch(() => {});
    audioContext = null;
    gainNode = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  speechSynthesis.cancel();
  ttsQueue.length = 0;

  setStatus("停止");
  log("sys", "停止しました");

  chrome.runtime.sendMessage({ type: "PROCESSOR_STOPPED" });
  setTimeout(() => window.close(), 1000);
}

// ウィンドウが閉じられたときのクリーンアップ
window.addEventListener("beforeunload", () => {
  if (isRunning) {
    isRunning = false;
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
    }
    chrome.runtime.sendMessage({ type: "PROCESSOR_STOPPED" });
  }
});

console.log("[Processor] Voice Bridge Processor 準備完了");
