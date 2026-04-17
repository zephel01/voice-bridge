/**
 * Live2D / pixi-live2d-display 初期化の前提セットアップ。
 *
 * pixi-live2d-display は内部で `window.PIXI` を参照するため、
 * 他のどのモジュールより先に PIXI をグローバルにセットする必要がある。
 *
 * main.tsx の一番最初でこのファイルを import する。
 */
import * as PIXI from "pixi.js";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).PIXI = PIXI;
