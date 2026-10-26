"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WsEvent } from "@/types";

export function useWebSocket(onEvent?: (event: WsEvent) => void) {
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsBase = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${window.location.host}`;
    const ws = new WebSocket(`${wsBase}/ws/live`);

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as WsEvent;
        handlerRef.current?.(event);
      } catch {
        // ignore malformed messages
      }
    };

    return ws;
  }, []);

  useEffect(() => {
    const ws = connect();
    return () => ws.close();
  }, [connect]);

  return { connected };
}
