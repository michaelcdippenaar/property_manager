<!--
  AgentMessagingView — Unified inbox (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-messaging.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { Filter, NotebookPen, Pencil, ExternalLink, NotebookPen as InternalNote, Send } from 'lucide-vue-next'

interface Thread {
  id: string
  name: string
  context: string
  preview: string
  time: string
  unread: boolean
}

const threads: Thread[] = [
  { id: 'vink', name: 'Piet Vink', context: '15 Andringa · WhatsApp',
    preview: 'Hi, geyser fixed, all good now. Tx for the quick turnaround 🙏',
    time: '2m', unread: true },
  { id: 'jvdm', name: 'J. van der Merwe', context: '15 Andringa · Email',
    preview: 'Approved the quote. Please proceed — invoice to me as usual.',
    time: '1h', unread: true },
  { id: 'ez', name: 'EZ Locksmith', context: 'Ticket #228 · SMS',
    preview: 'ETA 11:00 today. Bringing spare cylinder + keys.',
    time: '2h', unread: true },
  { id: 'jacobs', name: 'K. Jacobs', context: '22 Plein · In-app',
    preview: 'Questions about sign-up fees…',
    time: '1d', unread: false },
]

const active = ref('vink')
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Messaging</span></div>
      <div class="page-header-row">
        <div>
          <h1>Unified inbox</h1>
          <p class="sub">In-app · email · SMS · WhatsApp — same thread, every channel audit-logged.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Filter messages"><Filter :size="14" />Filter</button>
          <button class="btn" aria-label="Message templates"><NotebookPen :size="14" />Templates</button>
          <button class="btn primary" aria-label="New message"><Pencil :size="14" />New message</button>
        </div>
      </div>
    </div>

    <div class="messaging-wrap">
      <div class="thread-list">
        <div class="thread-list-head">Threads · 3 unread</div>
        <div
          v-for="t in threads"
          :key="t.id"
          class="thread-item"
          :class="{ active: active === t.id, read: !t.unread }"
          @click="active = t.id"
        >
          <div class="thread-item-top">
            <span v-if="t.unread" class="thread-dot" />
            <strong>{{ t.name }}</strong>
            <span class="thread-time">{{ t.time }}</span>
          </div>
          <div class="thread-ctx">{{ t.context }}</div>
          <div class="thread-preview" :class="{ muted: !t.unread }">{{ t.preview }}</div>
        </div>
      </div>

      <div class="chat-pane">
        <div class="chat-head">
          <div class="avatar" style="width:36px;height:36px;font-size:13px">PV</div>
          <div>
            <strong style="font-size:15px">Piet Vink</strong>
            <div style="font-size:12px;color:var(--muted)">Tenant · 15 Andringa · 3 channels active</div>
          </div>
          <button class="btn ghost" style="margin-left:auto" aria-label="Open god view"><ExternalLink :size="14" />God view</button>
        </div>

        <div class="chat-stamp center">Mon 14 Apr · 09:12 · WhatsApp inbound</div>
        <div class="bubble in">Hi Sarah, geyser fixed, all good now. Tx for the quick turnaround 🙏</div>

        <div class="chat-stamp right">Mon 14 Apr · 09:15 · In-app outbound</div>
        <div class="bubble-right">
          <div class="bubble out">Great! Please rate the supplier when you get a chance.</div>
        </div>

        <div class="chat-stamp center">Mon 14 Apr · 09:16 · WhatsApp inbound</div>
        <div class="bubble in">Will do, 5 stars already 👍</div>

        <div class="internal-note">
          <InternalNote :size="12" style="color:var(--warn);display:inline;vertical-align:middle" />
          <strong>Internal note · Sarah N · 09:20</strong><br>
          Tenant very happy with response — worth flagging for renewal discussion.
        </div>

        <div class="composer">
          <textarea placeholder="Reply in this thread..." />
          <div class="composer-foot">
            <span style="color:var(--muted)">Channel:</span>
            <label><input type="radio" name="ch" checked> In-app</label>
            <label><input type="radio" name="ch"> WhatsApp</label>
            <label><input type="radio" name="ch"> SMS</label>
            <label><input type="radio" name="ch"> Email</label>
            <button class="btn primary" style="margin-left:auto" aria-label="Send message"><Send :size="14" />Send</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style>
.agent-shell .messaging-wrap {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 0;
  padding: 20px 32px;
}
.agent-shell .thread-list {
  border: 1px solid var(--line);
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  background: #fff;
  overflow: hidden;
}
.agent-shell .thread-list-head {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  background: var(--paper);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  font-weight: 600;
}
.agent-shell .thread-item {
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
}
.agent-shell .thread-item.active { background: var(--navy-soft); }
.agent-shell .thread-item.read { opacity: 0.6; }
.agent-shell .thread-item-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
}
.agent-shell .thread-item-top strong { font-size: 13px; }
.agent-shell .thread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}
.agent-shell .thread-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--muted);
}
.agent-shell .thread-ctx {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.agent-shell .thread-preview {
  font-size: 13px;
  color: var(--ink);
}
.agent-shell .thread-preview.muted { color: var(--muted); }

.agent-shell .chat-pane {
  border: 1px solid var(--line);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  background: #fff;
  min-height: 560px;
  padding: 20px;
}
.agent-shell .chat-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 14px;
}
.agent-shell .chat-stamp {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 6px;
}
.agent-shell .chat-stamp.center { text-align: center; }
.agent-shell .chat-stamp.right { text-align: right; }
.agent-shell .bubble {
  display: inline-block;
  max-width: 70%;
  padding: 10px 14px;
  font-size: 13px;
  margin-bottom: 14px;
}
.agent-shell .bubble.in {
  /* WhatsApp brand inbound bubble — intentional product color */
  background: #DCF8C6; /* --channel-whatsapp */
  border-radius: 14px 14px 14px 4px;
}
.agent-shell .bubble.out {
  background: var(--navy);
  color: #fff;
  border-radius: 14px 14px 4px 14px;
  text-align: left;
}
.agent-shell .bubble-right {
  display: block;
  text-align: right;
  margin-bottom: 14px;
}
.agent-shell .internal-note {
  background: var(--warn-soft);
  border-left: 3px solid var(--warn);
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--ink);
  margin: 14px 0;
}
.agent-shell .composer {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  margin-top: 20px;
}
.agent-shell .composer textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 13px;
  min-height: 50px;
}
.agent-shell .composer-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 12px;
}
</style>
