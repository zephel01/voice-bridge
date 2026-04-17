// pixi-live2d-display の初期化より先に PIXI をグローバル化する
import "./live2d-setup";

import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

// NOTE: StrictMode は useEffect を 2 回走らせるため、PIXI.Application/Live2DModel
// の二重初期化で WebGL コンテキストが壊れる事例がある。本アプリでは外しておく。
ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
