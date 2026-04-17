/// <reference types="vite/client" />

declare module "pixi-live2d-display";
declare module "pixi-live2d-display/cubism4";
declare module "pixi-live2d-display/cubism2";
declare module "pixi-live2d-display/lib/cubism4";
declare module "pixi-live2d-display/lib/cubism2";

interface Window {
  voiceBridge?: { version: string };
  PIXI?: unknown;
}
