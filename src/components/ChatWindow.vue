<template>
  <section class="chat-window">
    <template v-if="conversation">
      <div class="chat-head">
        <h2>{{ conversation.title }}</h2>
        <button
          class="profile-toggle"
          type="button"
          title="查看好友资料"
          @click="$emit('toggle-profile')"
        >
          <i class="fa-solid fa-circle-info"></i>
        </button>
      </div>

      <div ref="feedRef" class="message-feed">
        <div v-if="loading" class="feed-state">正在加载消息...</div>
        <template v-else-if="messages.length">
          <article
            v-for="message in messages"
            :key="message.id"
            :class="['message-item', { self: message.senderId === currentUserId }]"
          >
            <img
              :src="message.senderAvatar"
              :alt="message.senderName"
              class="message-avatar"
            />

            <div class="message-main">
              <div class="message-meta">
                <strong>{{ message.senderName }}</strong>
                <time>{{ formatTimestamp(message.createdAt) }}</time>
              </div>
              <div class="message-bubble">{{ message.content }}</div>
            </div>
          </article>
        </template>
        <div v-else class="feed-state">发送第一条消息，开始聊天。</div>
      </div>

      <form class="composer" @submit.prevent="submitMessage">
        <div class="composer-row">
          <textarea
            ref="textareaRef"
            v-model="draft"
            rows="1"
            maxlength="1000"
            placeholder="输入消息"
            @keydown.enter.exact.prevent="submitMessage"
          ></textarea>
          <button type="submit" :disabled="!draft.trim()">发送</button>
        </div>
        <div class="composer-meta">
          <span>{{ draft.trim().length }}/1000</span>
        </div>
      </form>
    </template>

    <div v-else class="empty-chat">
      <h2>选择一个会话</h2>
      <p>从左侧打开已有会话，或先按账号添加好友。</p>
    </div>
  </section>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue';

const emit = defineEmits(['send', 'toggle-profile']);

const props = defineProps({
  conversation: {
    type: Object,
    default: null
  },
  messages: {
    type: Array,
    default: () => []
  },
  currentUserId: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const draft = ref('');
const feedRef = ref(null);
const textareaRef = ref(null);

const scrollToBottom = async () => {
  await nextTick();
  if (feedRef.value) {
    feedRef.value.scrollTop = feedRef.value.scrollHeight;
  }
};

const resizeTextarea = async () => {
  await nextTick();
  if (!textareaRef.value) {
    return;
  }

  textareaRef.value.style.height = 'auto';
  textareaRef.value.style.height = `${Math.min(textareaRef.value.scrollHeight, 96)}px`;
};

watch(
  () => props.conversation?.id,
  () => {
    draft.value = '';
    resizeTextarea();
  }
);

watch(
  () => props.messages.length,
  () => {
    scrollToBottom();
  }
);

watch(
  draft,
  () => {
    resizeTextarea();
  },
  { immediate: true }
);

const submitMessage = () => {
  const content = draft.value.trim();
  if (!content) {
    return;
  }

  emit('send', content);
  draft.value = '';
};

const formatTimestamp = (timestamp) =>
  new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(timestamp));
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: transparent;
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px 14px;
  border-bottom: 1px solid var(--border-secondary);
}

.chat-head h2 {
  color: var(--text-primary);
  font-size: 0.94rem;
  font-weight: 600;
  line-height: 1.2;
}

.profile-toggle {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--surface-secondary);
  color: var(--text-primary);
  transition:
    transform 0.18s ease,
    background 0.18s ease;
}

.profile-toggle:hover {
  transform: translateY(-1px);
  background: var(--surface-primary);
}

.message-feed {
  flex: 1;
  min-height: 0;
  padding: 16px 18px;
  overflow-y: auto;
  scrollbar-width: none;
}

.message-feed::-webkit-scrollbar {
  display: none;
}

.message-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.message-item.self {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
}

.message-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: min(72%, 440px);
}

.message-item.self .message-main {
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  color: var(--text-tertiary);
  font-size: 0.68rem;
}

.message-meta strong {
  color: var(--text-secondary);
  font-weight: 500;
}

.message-bubble {
  display: inline-block;
  width: fit-content;
  max-width: 100%;
  padding: 10px 13px;
  border-radius: 14px;
  background: var(--bubble-other-bg);
  color: var(--text-primary);
  font-size: 0.8rem;
  line-height: 1.58;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-item.self .message-bubble {
  background: var(--bubble-self-bg);
  color: var(--bubble-self-text);
  border-top-right-radius: 5px;
}

.message-item:not(.self) .message-bubble {
  border-top-left-radius: 5px;
}

.feed-state {
  color: var(--text-tertiary);
  font-size: 0.78rem;
}

.composer {
  padding: 12px 14px 14px;
  border-top: 1px solid var(--border-secondary);
  background: var(--surface-tertiary);
}

.composer-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: end;
}

.composer textarea {
  width: 100%;
  appearance: none;
  -webkit-appearance: none;
  resize: none;
  overflow-y: hidden;
  min-height: 40px;
  max-height: 96px;
  padding: 10px 12px;
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 0.8rem;
  line-height: 1.5;
  scrollbar-width: none;
}

.composer textarea::placeholder {
  color: var(--text-tertiary);
}

.composer textarea:focus {
  outline: 1px solid var(--accent);
}

.composer textarea::-webkit-scrollbar {
  display: none;
}

.composer button {
  min-width: 58px;
  height: 40px;
  padding: 0 15px;
  border-radius: 14px;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.composer button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.composer-meta {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
  color: var(--text-tertiary);
  font-size: 0.68rem;
}

.empty-chat {
  display: grid;
  place-items: center;
  gap: 8px;
  height: 100%;
  padding: 24px;
  text-align: center;
}

.empty-chat h2 {
  color: var(--text-primary);
  font-size: 1rem;
}

.empty-chat p {
  color: var(--text-tertiary);
  font-size: 0.8rem;
}

@media (max-width: 640px) {
  .chat-head,
  .message-feed,
  .composer {
    padding-left: 12px;
    padding-right: 12px;
  }

  .message-main {
    max-width: 84%;
  }
}
</style>
