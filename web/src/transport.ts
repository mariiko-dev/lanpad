import { useCallback, useEffect, useRef, useState } from "react";

import { MAX_EVENTS, parseState, type AgentState, type Event } from "./protocol";

const FLUSH_HEARTBEAT_MS = 25_000;
const RECONNECT_DELAY_MS = 1_000;

/**
 * Events waiting for the next frame.
 *
 * When the connection stalls mid-drag the queue would grow without bound,
 * and the agent refuses packets over MAX_EVENTS outright — losing the
 * recent moves along with the stale ones. Dropping the oldest keeps the
 * cursor responsive the moment the link comes back.
 */
export class EventQueue {
  private events: Event[] = [];

  push(event: Event): void {
    this.events.push(event);
    if (this.events.length > MAX_EVENTS) {
      this.events.splice(0, this.events.length - MAX_EVENTS);
    }
  }

  drain(): Event[] {
    const drained = this.events;
    this.events = [];
    return drained;
  }

  size(): number {
    return this.events.length;
  }
}

export interface Transport {
  send: (event: Event) => void;
  connected: boolean;
  state: AgentState | null;
}

export function useTransport(token: string): Transport {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<AgentState | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const queueRef = useRef(new EventQueue());

  useEffect(() => {
    if (!token) {
      return undefined;
    }
    const query = `t=${encodeURIComponent(token)}`;
    let stopped = false;
    let frame = 0;

    const postFallback = (payload: string): void => {
      void fetch(`/e?${query}`, { method: "POST", body: payload, keepalive: true })
        .catch(() => undefined);
    };

    const connect = (): void => {
      if (stopped) {
        return;
      }
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${scheme}://${location.host}/ws?${query}`);
      socketRef.current = socket;
      socket.onopen = () => setConnected(true);
      socket.onmessage = (message) => {
        const next = parseState(String(message.data));
        if (next) {
          setState(next);
        }
      };
      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (!stopped) {
          window.setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
      socket.onerror = () => socket.close();
    };
    connect();

    const heartbeat = window.setInterval(() => {
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send("[]");
      }
    }, FLUSH_HEARTBEAT_MS);

    const flush = (): void => {
      if (queueRef.current.size() > 0) {
        const payload = JSON.stringify(queueRef.current.drain());
        const socket = socketRef.current;
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(payload);
        } else {
          postFallback(payload);
        }
      }
      frame = requestAnimationFrame(flush);
    };
    frame = requestAnimationFrame(flush);

    return () => {
      stopped = true;
      window.clearInterval(heartbeat);
      cancelAnimationFrame(frame);
      socketRef.current?.close();
    };
  }, [token]);

  const send = useCallback((event: Event) => {
    queueRef.current.push(event);
  }, []);

  return { send, connected, state };
}
