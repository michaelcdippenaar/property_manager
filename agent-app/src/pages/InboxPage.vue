<template>
  <q-page class="inbox-page">

    <!-- ── Channel filter ── -->
    <div class="channel-strip">
      <button
        v-for="c in channels"
        :key="c.id"
        class="channel-chip"
        :class="{ 'channel-chip--active': activeChannel === c.id }"
        @click="activeChannel = c.id"
      >
        <q-icon :name="c.icon" size="14px" />
        <span>{{ c.label }}</span>
        <span v-if="c.unread" class="channel-badge">{{ c.unread }}</span>
      </button>
    </div>

    <!-- ── AI digest ── -->
    <q-card flat class="digest-card">
      <div class="digest-head">
        <q-icon name="auto_awesome" size="16px" color="secondary" />
        <span class="digest-title">AI digest</span>
      </div>
      <div class="digest-body">
        <div class="digest-stat">
          <strong>3</strong> hot leads pre-qualified this morning
        </div>
        <div class="digest-stat">
          <strong>7</strong> threads waiting on your reply &gt; 2h
        </div>
        <div class="digest-stat">
          <strong>2</strong> landlords asking for updates
        </div>
      </div>
    </q-card>

    <!-- ── Thread list ── -->
    <q-pull-to-refresh @refresh="loadData">
      <q-card flat class="thread-card">
        <q-list separator>
          <q-item
            v-for="t in filteredThreads"
            :key="t.id"
            clickable
            v-ripple
            class="thread-item"
            :class="{ 'thread-item--unread': t.unread }"
          >
            <q-item-section avatar>
              <div class="thread-avatar">
                <q-avatar :size="AVATAR_LIST" :color="channelColor(t.channel)" text-color="white">
                  {{ t.initials }}
                </q-avatar>
                <div class="thread-channel" :style="{ background: channelHex(t.channel) }">
                  <q-icon :name="channelIcon(t.channel)" size="10px" color="white" />
                </div>
              </div>
            </q-item-section>

            <q-item-section>
              <q-item-label class="thread-top-row">
                <span class="thread-name">{{ t.name }}</span>
                <span class="thread-time">{{ t.time }}</span>
              </q-item-label>
              <q-item-label caption class="thread-preview" lines="2">{{ t.preview }}</q-item-label>
              <div class="thread-meta" v-if="t.tags.length > 0">
                <span
                  v-for="tag in t.tags"
                  :key="tag.label"
                  class="thread-tag"
                  :class="`thread-tag--${tag.tone}`"
                >
                  {{ tag.label }}
                </span>
              </div>
            </q-item-section>

            <q-item-section side v-if="t.unread">
              <div class="unread-dot" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <div class="tab-bar-spacer" />
    </q-pull-to-refresh>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { AVATAR_LIST } from '../utils/designTokens'

const setPageTitle = inject<(t: string | null) => void>('setPageTitle')

type Channel = 'all' | 'whatsapp' | 'p24' | 'instagram' | 'email'
const activeChannel = ref<Channel>('all')

// Stubbed data — wires up when unified inbox backend lands
const threads = ref<Array<{
  id: number
  name: string
  initials: string
  channel: Exclude<Channel, 'all'>
  preview: string
  time: string
  unread: boolean
  tags: Array<{ label: string, tone: string }>
}>>([
  {
    id: 1,
    name: 'John Dlamini',
    initials: 'JD',
    channel: 'whatsapp',
    preview: 'Pre-qualified by AI · Budget R 15–18k · Move 1 May · 2 bed · Employed Standard Bank · Credit passed.',
    time: '08:42',
    unread: true,
    tags: [
      { label: 'Pre-qualified', tone: 'positive' },
      { label: 'Hot lead',      tone: 'accent' },
    ],
  },
  {
    id: 2,
    name: 'Property24 enquiry · 14 Bosch St',
    initials: 'P24',
    channel: 'p24',
    preview: '"Is it still available? Can I book a viewing on Saturday?" — 3 enquiries on this listing today.',
    time: '08:10',
    unread: true,
    tags: [
      { label: 'Needs reply', tone: 'warn' },
    ],
  },
  {
    id: 3,
    name: 'Nomvula Zulu',
    initials: 'NZ',
    channel: 'instagram',
    preview: 'DM · "Saw your reel on De Klerk — what\'s the deposit?" — AI drafted a reply for you.',
    time: 'Yesterday',
    unread: true,
    tags: [
      { label: 'AI reply drafted', tone: 'primary' },
    ],
  },
  {
    id: 4,
    name: 'M. Adams (Landlord)',
    initials: 'MA',
    channel: 'email',
    preview: 'Any update on 14 Bosch St? I see there are 6 viewings booked this week — who are the strongest?',
    time: 'Yesterday',
    unread: false,
    tags: [
      { label: 'Landlord', tone: 'primary' },
    ],
  },
  {
    id: 5,
    name: 'Andrew Meyer',
    initials: 'AM',
    channel: 'whatsapp',
    preview: 'Application submitted. Payslips and bank statements uploaded. Waiting on credit.',
    time: 'Tue',
    unread: false,
    tags: [
      { label: 'Application', tone: 'primary' },
    ],
  },
])

const channels = computed(() => ([
  { id: 'all' as Channel,       label: 'All',       icon: 'inbox',           unread: threads.value.filter((t) => t.unread).length },
  { id: 'whatsapp' as Channel,  label: 'WhatsApp',  icon: 'chat',            unread: threads.value.filter((t) => t.unread && t.channel === 'whatsapp').length },
  { id: 'p24' as Channel,       label: 'P24',       icon: 'language',        unread: threads.value.filter((t) => t.unread && t.channel === 'p24').length },
  { id: 'instagram' as Channel, label: 'Instagram', icon: 'photo_camera',    unread: threads.value.filter((t) => t.unread && t.channel === 'instagram').length },
  { id: 'email' as Channel,     label: 'Email',     icon: 'mail_outline',    unread: threads.value.filter((t) => t.unread && t.channel === 'email').length },
]))

const filteredThreads = computed(() => {
  if (activeChannel.value === 'all') return threads.value
  return threads.value.filter((t) => t.channel === activeChannel.value)
})

function channelColor(c: Exclude<Channel, 'all'>): string {
  return {
    whatsapp:  'positive',
    p24:       'primary',
    instagram: 'secondary',
    email:     'grey-7',
  }[c]
}

function channelIcon(c: Exclude<Channel, 'all'>): string {
  return {
    whatsapp:  'chat',
    p24:       'language',
    instagram: 'photo_camera',
    email:     'mail_outline',
  }[c]
}

function channelHex(c: Exclude<Channel, 'all'>): string {
  return {
    whatsapp:  '#25D366',
    p24:       '#2B2D6E',
    instagram: '#E1306C',
    email:     '#6b7280',
  }[c]
}

async function loadData(done?: () => void) {
  done?.()
}

onMounted(() => {
  setPageTitle?.('Inbox')
})
</script>

<style scoped lang="scss">
.inbox-page {
  background: var(--klikk-surface);
  padding: 10px 0 0;
  min-height: 100vh;
}

/* ── Channel filter ── */
.channel-strip {
  display: flex;
  gap: 6px;
  padding: 8px 16px 12px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.channel-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  white-space: nowrap;
  transition: all 0.15s;

  &--active {
    background: $primary;
    border-color: $primary;
    color: white;
  }

  &:active:not(&--active) {
    opacity: 0.7;
  }
}

.channel-badge {
  background: $secondary;
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 0 6px;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  border-radius: 999px;
  margin-left: 2px;
}

/* ── AI digest ── */
.digest-card {
  background: linear-gradient(135deg, rgba(43, 45, 110, 0.04) 0%, rgba(255, 61, 127, 0.04) 100%);
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  margin: 0 16px 14px;
  padding: 12px 14px;
}

.digest-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.digest-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--klikk-text-primary);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.digest-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}

.digest-stat {
  font-size: 13px;
  color: var(--klikk-text-secondary);
  line-height: 1.4;

  strong {
    color: $primary;
    font-weight: 800;
  }
}

/* ── Threads ── */
.thread-card {
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  box-shadow: var(--klikk-shadow-soft);
  margin: 0 16px;
  overflow: hidden;
}

.thread-item--unread .thread-name {
  font-weight: 700;
}

.thread-avatar {
  position: relative;
  width: 40px;
  height: 40px;
}

.thread-channel {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 16px;
  height: 16px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid white;
}

.thread-top-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.thread-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--klikk-text-primary);
  letter-spacing: -0.01em;
}

.thread-time {
  font-size: 11px;
  color: var(--klikk-text-muted);
  flex-shrink: 0;
}

.thread-preview {
  color: var(--klikk-text-secondary);
  line-height: 1.4;
  margin-top: 2px;
}

.thread-meta {
  display: flex;
  gap: 5px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.thread-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  letter-spacing: 0.02em;

  &--positive { background: rgba(20, 184, 166, 0.12); color: $positive; }
  &--accent   { background: rgba(255, 61, 127, 0.12); color: $secondary; }
  &--primary  { background: rgba(43, 45, 110, 0.10);  color: $primary; }
  &--warn     { background: rgba(245, 158, 11, 0.14); color: $warning; }
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: $secondary;
}

.tab-bar-spacer {
  height: calc(90px + env(safe-area-inset-bottom, 0px));
}
</style>
