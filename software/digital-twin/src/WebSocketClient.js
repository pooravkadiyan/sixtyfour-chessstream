/**
 * Live link to a ChessStream board (port 81) or the Python relay (port 8080 /ws).
 * Firmware messages: {event: lift|place|move|board_state|connected, ...}
 */

export class BoardSocket {
  constructor(onEvent, onStatus) {
    this.onEvent = onEvent;
    this.onStatus = onStatus;
    this.ws = null;
    this.url = "";
  }

  get connected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /** A board listens on :81. Anything else is treated as the relay, which accepts commands. */
  get listenOnly() {
    return /:81(\/|$)/.test(this.url);
  }

  connect(url) {
    this.disconnect();
    this.url = url;
    this.onStatus("Connecting…", "sim");
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      this.onStatus(String(err.message || err), "bad");
      return;
    }
    this.ws = ws;
    ws.onopen = () => this.onStatus(`Live ${url}`, "live");
    ws.onclose = () => {
      if (this.ws === ws) this.onStatus("Disconnected — simulator is active", "sim");
    };
    ws.onerror = () => this.onStatus(`Could not open ${url}`, "bad");
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        this.onEvent(msg, "remote");
      } catch {
        /* ignore non-JSON keepalives */
      }
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }

  send(obj) {
    if (!this.connected || this.listenOnly) return;
    this.ws.send(JSON.stringify(obj));
  }
}
