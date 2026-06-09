<template>
  <aside class="conversation-panel">
    <div class="panel-tools">
      <input v-model="keyword" class="search-box" type="text" placeholder="搜索会话" />
    </div>

    <div v-if="loading" class="panel-state">正在加载...</div>
    <div v-else-if="filteredConversations.length === 0" class="panel-state">
      暂无会话
    </div>

    <ul v-else class="conversation-list">
      <li
        v-for="conversation in filteredConversations"
        :key="conversation.id"
        :class="[
          'conversation-item',
          { active: conversation.id === selectedConversationId }
        ]"
        @click="$emit('select', conversation.id)"
      >
        <div class="conversation-avatar-wrap">
          <img
            :src="conversation.avatarUrl"
            :alt="conversation.title"
            class="conversation-avatar"
          />
          <span v-if="conversation.unreadCount" class="unread-badge">
            {{ conversation.unreadCount > 99 ? '99+' : conversation.unreadCount }}
          </span>
        </div>

        <div class="conversation-meta">
          <div class="conversation-row">
            <strong>{{ conversation.title }}</strong>
            <time>{{ formatTimestamp(conversation.updatedAt) }}</time>
          </div>
          <p>{{ conversation.lastMessage || '暂无消息' }}</p>
        </div>
      </li>
    </ul>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue';

defineEmits(['select']);

const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  selectedConversationId: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const keyword = ref('');

const filteredConversations = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLowerCase();

  return props.conversations.filter((conversation) => {
    if (!normalizedKeyword) {
      return true;
    }

    return [conversation.title, conversation.lastMessage, conversation.subtitle]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(normalizedKeyword));
  });
});

const formatTimestamp = (timestamp) => {
  if (!timestamp) {
    return '';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(timestamp));
};
</script>

<style scoped>
.conversation-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid var(--border-secondary);
  background: var(--surface-tertiary);
}

.panel-tools {
  padding: 14px;
}

.search-box {
  width: 100%;
  height: 38px;
  padding: 0 13px;
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 0.8rem;
}

.search-box::placeholder {
  color: var(--text-tertiary);
}

.search-box:focus {
  outline: 1px solid var(--accent);
}

.panel-state {
  padding: 0 14px 14px;
  color: var(--text-tertiary);
  font-size: 0.78rem;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 10px 12px;
  overflow-y: auto;
}

.conversation-item {
  display: flex;
  gap: 12px;
  padding: 12px 10px;
  border-radius: 16px;
  background: transparent;
  cursor: pointer;
  transition: background 0.18s ease;
}

.conversation-item:hover {
  background: var(--surface-secondary);
}

.conversation-item.active {
  background: var(--surface-active);
}

.conversation-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.conversation-avatar {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  object-fit: cover;
}

.unread-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ff4d4f;
  color: #fff;
  font-size: 0.66rem;
  line-height: 18px;
  text-align: center;
}

.conversation-meta {
  min-width: 0;
  flex: 1;
}

.conversation-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
}

.conversation-row strong {
  font-size: 0.82rem;
  font-weight: 500;
}

.conversation-row time {
  color: var(--text-tertiary);
  font-size: 0.7rem;
  white-space: nowrap;
}

.conversation-meta p {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 0.75rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .conversation-panel {
    border-right: 0;
    border-bottom: 1px solid var(--border-secondary);
  }
}
</style>
