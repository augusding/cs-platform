/**
 * CS Platform Chat Widget (hand-transpiled from widget.ts)
 * Usage:
 *   <script>window.CS_CONFIG = { botId: "...", apiKey: "cs_bot_...", primaryColor: "#1565C0" }</script>
 *   <script src="/widget.js" async></script>
 */
(function () {
  var config = window.CS_CONFIG || { botId: "" };
  if (!config.botId || !config.apiKey) {
    console.warn("[CS Widget] botId and apiKey are required");
    return;
  }

  var BASE_URL = config.baseUrl || window.location.origin;
  var COLOR    = config.primaryColor || "#1565C0";
  var POS      = config.position || "bottom-right";
  var SIDE     = POS.indexOf("right") >= 0 ? "right:24px" : "left:24px";
  var VISITOR_ID = "cs_" + Math.random().toString(36).slice(2);

  var host = document.createElement("div");
  document.body.appendChild(host);
  var shadow = host.attachShadow({ mode: "open" });

  var style = document.createElement("style");
  style.textContent =
    "* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, sans-serif; }" +
    "#bubble { position: fixed; bottom: 24px; " + SIDE + "; width: 56px; height: 56px;" +
    "  background: " + COLOR + "; border-radius: 50%; cursor: pointer;" +
    "  box-shadow: 0 4px 12px rgba(0,0,0,.2); display: flex;" +
    "  align-items: center; justify-content: center; z-index: 99999; transition: transform .2s; }" +
    "#bubble:hover { transform: scale(1.08); }" +
    "#bubble svg { width: 26px; height: 26px; fill: white; }" +
    "#window { position: fixed; bottom: 92px; " + SIDE + "; width: 360px; height: 520px;" +
    "  background: #fff; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,.15);" +
    "  display: flex; flex-direction: column; z-index: 99998; transition: opacity .2s, transform .2s; }" +
    "#window.hidden { opacity: 0; pointer-events: none; transform: translateY(12px); }" +
    "#header { background: " + COLOR + "; color: #fff; padding: 14px 16px;" +
    "  border-radius: 16px 16px 0 0; font-size: 15px; font-weight: 600; }" +
    "#messages { flex: 1; overflow-y: auto; padding: 12px; display: flex;" +
    "  flex-direction: column; gap: 8px; }" +
    ".msg { max-width: 80%; padding: 8px 12px; border-radius: 12px;" +
    "  font-size: 14px; line-height: 1.5; word-break: break-word; }" +
    ".msg.user { align-self: flex-end; background: " + COLOR + "; color: #fff;" +
    "  border-radius: 12px 12px 2px 12px; }" +
    ".msg.bot  { align-self: flex-start; background: #f0f4f8; color: #2c3e50;" +
    "  border-radius: 12px 12px 12px 2px; }" +
    "#input-row { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #eee; }" +
    "#input { flex: 1; border: 1px solid #ddd; border-radius: 8px;" +
    "  padding: 8px 10px; font-size: 14px; outline: none; }" +
    "#input:focus { border-color: " + COLOR + "; }" +
    "#send { background: " + COLOR + "; color: #fff; border: none; border-radius: 8px;" +
    "  padding: 8px 14px; cursor: pointer; font-size: 14px; }" +
    "#send:hover { opacity: .88; }";
  shadow.appendChild(style);

  var bubble = document.createElement("div");
  bubble.id = "bubble";
  bubble.innerHTML =
    '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
  shadow.appendChild(bubble);

  var win = document.createElement("div");
  win.id = "window";
  win.className = "hidden";
  win.innerHTML =
    '<div id="header">智能客服</div>' +
    '<div id="messages"></div>' +
    '<div id="input-row">' +
    '  <input id="input" type="text" placeholder="输入消息…" />' +
    '  <button id="send">发送</button>' +
    '</div>';
  shadow.appendChild(win);

  var messagesEl = shadow.getElementById("messages");
  var inputEl    = shadow.getElementById("input");
  var sendEl     = shadow.getElementById("send");

  var ws = null;
  var sessionId = null;
  var currentBotMsg = null;
  var isOpen = false;

  function appendMsg(text, role) {
    var div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function connect() {
    if (ws && ws.readyState <= WebSocket.OPEN) return;
    var proto = BASE_URL.indexOf("https") === 0 ? "wss" : "ws";
    var url = proto + "://" + BASE_URL.replace(/^https?:\/\//, "")
      + "/api/chat/" + config.botId
      + "?key=" + encodeURIComponent(config.apiKey)
      + "&visitor_id=" + encodeURIComponent(VISITOR_ID)
      + (sessionId ? "&session_id=" + encodeURIComponent(sessionId) : "");

    ws = new WebSocket(url);

    ws.onmessage = function (e) {
      var msg = JSON.parse(e.data);
      if (msg.type === "connected") {
        sessionId = msg.session_id;
        appendMsg(msg.welcome, "bot");
      } else if (msg.type === "token") {
        if (!currentBotMsg) currentBotMsg = appendMsg("", "bot");
        currentBotMsg.textContent += msg.content;
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (msg.type === "done") {
        currentBotMsg = null;
        sendEl.removeAttribute("disabled");
        inputEl.removeAttribute("disabled");
      } else if (msg.type === "transfer") {
        appendMsg(msg.message, "bot");
      } else if (msg.type === "error") {
        if (currentBotMsg) { currentBotMsg.remove(); currentBotMsg = null; }
        appendMsg("发送失败，请重试", "bot");
        sendEl.removeAttribute("disabled");
        inputEl.removeAttribute("disabled");
      } else if (msg.type === "private_domain") {
        var card = document.createElement("div");
        card.className = "msg bot";
        card.style.padding = "12px";
        var html = "<p style='font-size:13px;margin-bottom:8px;'>"
          + (msg.message || "") + "</p>";
        if (msg.qr_code_url) {
          html += "<img src='" + msg.qr_code_url
            + "' style='width:120px;height:120px;display:block;'/>";
        }
        card.innerHTML = html;
        messagesEl.appendChild(card);
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (msg.type === "ping") {
        if (ws) ws.send(JSON.stringify({ type: "pong" }));
      }
    };

    ws.onerror = function () { appendMsg("连接错误，请刷新页面", "bot"); };
  }

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    appendMsg(text, "user");
    inputEl.value = "";
    sendEl.setAttribute("disabled", "true");
    inputEl.setAttribute("disabled", "true");
    ws.send(JSON.stringify({ type: "message", content: text, visitor_id: VISITOR_ID }));
  }

  bubble.addEventListener("click", function () {
    isOpen = !isOpen;
    win.classList.toggle("hidden", !isOpen);
    if (isOpen && (!ws || ws.readyState > WebSocket.OPEN)) connect();
  });

  sendEl.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });
})();
