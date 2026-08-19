import { useEffect } from "react";

/**
 * Loads the Crisp Chat widget when REACT_APP_CRISP_WEBSITE_ID is set.
 * Gracefully no-ops when the env var is empty so the app stays chat-free until you register at crisp.chat.
 */
export default function CrispChat() {
  useEffect(() => {
    const id = process.env.REACT_APP_CRISP_WEBSITE_ID;
    if (!id) return;
    if (window.$crisp) return; // already loaded
    window.$crisp = [];
    window.CRISP_WEBSITE_ID = id;
    const script = document.createElement("script");
    script.src = "https://client.crisp.chat/l.js";
    script.async = true;
    document.head.appendChild(script);
    return () => {
      // Crisp doesn't expose an unload; we simply leave it — chat should persist across route changes.
    };
  }, []);
  return null;
}
