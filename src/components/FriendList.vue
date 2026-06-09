<template>
  <section class="friends-page">
    <div class="friends-layout">
      <section class="toolbar-card">
        <div class="toolbar-copy">
          <span class="eyebrow">好友验证</span>
          <h2>搜索账号并发起好友申请</h2>
          <p>验证消息会随申请一起发送，对方同意后即可开始聊天。</p>
        </div>

        <div class="toolbar-form">
          <label class="input-group">
            <span>账号</span>
            <input
              v-model="keyword"
              class="input"
              type="text"
              placeholder="输入手机号或昵称"
            />
          </label>

          <label class="input-group">
            <span>验证消息</span>
            <input
              v-model.trim="requestMessage"
              class="input"
              type="text"
              :maxlength="friendRequestMessageMaxLength"
              placeholder="你好，我想添加你为好友"
            />
            <small class="field-meta">
              {{ requestMessage.length }}/{{ friendRequestMessageMaxLength }}
            </small>
          </label>
        </div>

        <div class="toolbar-meta">
          <span class="meta-chip">
            待处理
            <strong>{{ pendingIncomingRequests.length }}</strong>
          </span>
          <span class="meta-chip">
            已发送
            <strong>{{ outgoingRequests.length }}</strong>
          </span>
        </div>
      </section>

      <div
        :class="[
          'friends-main',
          { 'friends-main-single': !incomingRequests.length && !outgoingRequests.length }
        ]"
      >
        <aside
          v-if="incomingRequests.length || outgoingRequests.length"
          class="request-column"
        >
          <section v-if="incomingRequests.length" class="content-card compact-card">
            <div class="section-heading compact">
              <div>
                <h3>收到的申请</h3>
                <p>待处理与历史记录都会保留</p>
              </div>
              <span class="section-count">{{ incomingRequests.length }}</span>
            </div>
            <div class="card-scroll">
              <ul v-if="pendingIncomingRequests.length" class="request-list">
                <li
                  v-for="requestItem in pendingIncomingRequests"
                  :key="requestItem.id"
                  class="request-card"
                >
                  <img
                    :src="requestItem.user.avatarUrl"
                    :alt="requestItem.user.userName"
                    class="avatar"
                  />
                  <div class="request-body">
                    <div class="request-row">
                      <div class="request-info">
                        <div class="user-row">
                          <div>
                            <strong>{{ requestItem.user.userName }}</strong>
                            <span>{{ requestItem.user.telephone }}</span>
                          </div>
                        </div>
                        <p class="request-message">
                          {{ requestItem.message || '请求添加你为好友' }}
                        </p>
                      </div>
                      <div class="request-actions stacked">
                        <button
                          class="action-button"
                          type="button"
                          @click="$emit('accept-request', requestItem.id)"
                        >
                          同意
                        </button>
                        <button
                          class="action-button secondary"
                          type="button"
                          @click="$emit('reject-request', requestItem.id)"
                        >
                          拒绝
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              </ul>

              <ul v-if="historyIncomingRequests.length" class="request-list history-list">
                <li
                  v-for="requestItem in historyIncomingRequests"
                  :key="requestItem.id"
                  class="request-card history-card"
                >
                  <img
                    :src="requestItem.user.avatarUrl"
                    :alt="requestItem.user.userName"
                    class="avatar"
                  />
                  <div class="request-body">
                    <div class="user-row">
                      <div>
                        <strong>{{ requestItem.user.userName }}</strong>
                        <span>{{ requestItem.user.telephone }}</span>
                      </div>
                      <span class="status-chip muted">
                        {{ getRequestStatusLabel(requestItem.status) }}
                      </span>
                    </div>
                    <p class="request-message">
                      {{ requestItem.message || '请求添加你为好友' }}
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </section>

          <section v-if="outgoingRequests.length" class="content-card compact-card">
            <div class="section-heading compact">
              <div>
                <h3>发送记录</h3>
                <p>可以看到对方是否已经同意或拒绝</p>
              </div>
              <span class="section-count">{{ outgoingRequests.length }}</span>
            </div>

            <div class="card-scroll">
              <ul v-if="pendingOutgoingRequests.length" class="request-list">
                <li
                  v-for="requestItem in pendingOutgoingRequests"
                  :key="requestItem.id"
                  class="request-card outgoing-card"
                >
                  <img
                    :src="requestItem.user.avatarUrl"
                    :alt="requestItem.user.userName"
                    class="avatar"
                  />
                  <div class="request-body">
                    <div class="user-row">
                      <div>
                        <strong>{{ requestItem.user.userName }}</strong>
                        <span>{{ requestItem.user.telephone }}</span>
                      </div>
                      <span class="status-chip muted">等待处理</span>
                    </div>
                    <p class="request-message">
                      {{ requestItem.message || '好友申请已发送，等待对方处理。' }}
                    </p>
                  </div>
                </li>
              </ul>

              <ul v-if="historyOutgoingRequests.length" class="request-list history-list">
                <li
                  v-for="requestItem in historyOutgoingRequests"
                  :key="requestItem.id"
                  class="request-card history-card outgoing-card"
                >
                  <img
                    :src="requestItem.user.avatarUrl"
                    :alt="requestItem.user.userName"
                    class="avatar"
                  />
                  <div class="request-body">
                    <div class="user-row">
                      <div>
                        <strong>{{ requestItem.user.userName }}</strong>
                        <span>{{ requestItem.user.telephone }}</span>
                      </div>
                      <span
                        :class="[
                          'status-chip',
                          requestItem.status === 'accepted' ? 'muted' : 'subtle'
                        ]"
                      >
                        {{ getRequestStatusLabel(requestItem.status) }}
                      </span>
                    </div>
                    <p class="request-message">
                      {{ requestItem.message || '好友申请已发送。' }}
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </section>
        </aside>

        <section class="content-card result-section">
          <div class="section-heading">
            <div>
              <h3>搜索结果</h3>
              <p>已是好友时可以直接发消息，其他情况按状态显示</p>
            </div>
            <span v-if="filteredUsers.length" class="section-count">
              {{ filteredUsers.length }}
            </span>
          </div>

          <div v-if="loading" class="empty-state">正在搜索...</div>
          <div v-else-if="!keyword.trim()" class="empty-state">输入账号开始搜索</div>
          <div v-else-if="filteredUsers.length === 0" class="empty-state">
            没有找到匹配的用户
          </div>

          <div v-else class="card-scroll result-scroll">
            <ul class="result-grid">
              <li
                v-for="friend in filteredUsers"
                :key="friend.id"
                class="result-card"
              >
                <div class="result-user">
                  <img :src="friend.avatarUrl" :alt="friend.userName" class="avatar large" />
                  <div class="result-meta">
                    <strong>{{ friend.remark || friend.userName }}</strong>
                    <span v-if="friend.remark" class="result-name">{{ friend.userName }}</span>
                    <span>{{ friend.telephone }}</span>
                    <p>{{ friend.bio || '这个用户还没有填写个人资料。' }}</p>
                  </div>
                </div>

                <div class="result-footer">
                  <span v-if="friend.isFriend" class="status-chip muted">已是好友</span>
                  <span v-else-if="friend.outgoingRequest" class="status-chip muted">
                    已发送申请
                  </span>
                  <span v-else-if="friend.incomingRequest" class="status-chip muted">
                    等待你处理
                  </span>
                  <span v-else class="status-chip subtle">可添加</span>

                  <div class="result-actions">
                    <button
                      v-if="friend.isFriend"
                      class="action-button secondary"
                      type="button"
                      @click="$emit('open-chat', friend.id)"
                    >
                      发消息
                    </button>

                    <button
                      v-else-if="friend.outgoingRequest"
                      class="action-button secondary"
                      type="button"
                      disabled
                    >
                      已发送
                    </button>

                    <button
                      v-else-if="friend.incomingRequest"
                      class="action-button secondary"
                      type="button"
                      disabled
                    >
                      待处理
                    </button>

                    <button
                      v-else
                      class="action-button"
                      type="button"
                      @click="$emit('add-friend', { friendId: friend.id, message: requestMessage })"
                    >
                      发送申请
                    </button>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';

const emit = defineEmits([
  'search',
  'add-friend',
  'open-chat',
  'accept-request',
  'reject-request'
]);

const props = defineProps({
  users: {
    type: Array,
    default: () => []
  },
  incomingRequests: {
    type: Array,
    default: () => []
  },
  outgoingRequests: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const keyword = ref('');
const friendRequestMessageMaxLength = 50;
const requestMessage = ref('你好，我想添加你为好友');
let timer = null;

watch(keyword, (value) => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    emit('search', value);
  }, 250);
});

onBeforeUnmount(() => {
  clearTimeout(timer);
});

const filteredUsers = computed(() => props.users);
const pendingIncomingRequests = computed(() =>
  props.incomingRequests.filter((item) => item.status === 'pending')
);
const historyIncomingRequests = computed(() =>
  props.incomingRequests.filter((item) => item.status !== 'pending')
);
const pendingOutgoingRequests = computed(() =>
  props.outgoingRequests.filter((item) => item.status === 'pending')
);
const historyOutgoingRequests = computed(() =>
  props.outgoingRequests.filter((item) => item.status !== 'pending')
);

const getRequestStatusLabel = (status) => {
  if (status === 'accepted') {
    return '已同意';
  }
  if (status === 'rejected') {
    return '已拒绝';
  }
  return '待处理';
};
</script>

<style scoped>
.friends-page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 20px 20px;
}

.friends-layout {
  width: min(1120px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toolbar-card,
.content-card {
  border: 1px solid var(--border-secondary);
  border-radius: 24px;
  background: linear-gradient(180deg, var(--surface-secondary), var(--surface-tertiary));
  box-shadow: var(--shadow-soft);
}

.toolbar-card {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(360px, 1.3fr) auto;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
}

.toolbar-copy h2 {
  margin: 6px 0 8px;
  color: var(--text-primary);
  font-size: 1.05rem;
  line-height: 1.2;
  font-weight: 600;
}

.toolbar-copy p,
.section-heading p,
.result-meta p,
.user-row span,
.empty-state {
  color: var(--text-secondary);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--surface-primary);
  color: var(--text-tertiary);
  font-size: 0.68rem;
  letter-spacing: 0.06em;
}

.toolbar-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group span {
  color: var(--text-primary);
  font-size: 0.72rem;
  font-weight: 600;
}

.field-meta {
  color: var(--text-tertiary);
  font-size: 0.66rem;
  text-align: right;
}

.input {
  width: 100%;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--border-primary);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 0.76rem;
}

.input::placeholder {
  color: var(--text-tertiary);
}

.input:focus {
  outline: 1px solid var(--accent);
}

.toolbar-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border-secondary);
  border-radius: 999px;
  background: var(--surface-primary);
  color: var(--text-primary);
  font-size: 0.72rem;
}

.meta-chip strong {
  font-size: 0.76rem;
  font-weight: 700;
}

.friends-main {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  align-items: start;
  gap: 14px;
}

.friends-main-single {
  grid-template-columns: 1fr;
}

.request-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.content-card {
  padding: 18px;
}

.compact-card {
  background: var(--surface-secondary);
  max-height: min(56vh, 520px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-heading.compact {
  margin-bottom: 10px;
}

.section-heading h3 {
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 600;
}

.section-heading p {
  margin-top: 4px;
  font-size: 0.72rem;
}

.section-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--surface-primary);
  color: var(--text-primary);
  font-size: 0.7rem;
  font-weight: 600;
}

.request-list,
.result-grid {
  display: grid;
  gap: 10px;
}

.card-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.history-list {
  margin-top: 10px;
}

.request-card,
.result-card {
  border: 1px solid var(--border-secondary);
  border-radius: 18px;
  background: var(--surface-primary);
}

.history-card {
  opacity: 0.92;
}

.request-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
}

.outgoing-card {
  background: color-mix(in srgb, var(--surface-primary) 92%, var(--surface-secondary));
}

.request-body {
  min-width: 0;
}

.request-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.request-info {
  min-width: 0;
}

.user-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.user-row strong,
.result-meta strong {
  display: block;
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 600;
}

.result-name {
  color: var(--text-tertiary);
}

.user-row span,
.result-meta span,
.result-meta p,
.empty-state,
.request-message {
  font-size: 0.72rem;
  line-height: 1.5;
}

.request-message {
  margin-top: 6px;
  color: var(--text-secondary);
  word-break: break-word;
  white-space: pre-wrap;
}

.request-actions,
.result-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
}

.result-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.request-actions.stacked {
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  margin-top: 0;
  min-width: 72px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  object-fit: cover;
  background: var(--surface-secondary);
}

.avatar.large {
  width: 48px;
  height: 48px;
  border-radius: 16px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 0.68rem;
  white-space: nowrap;
}

.status-chip.muted {
  background: var(--surface-secondary);
  color: var(--text-primary);
}

.status-chip.subtle {
  background: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-tertiary);
}

.action-button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 0.72rem;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease,
    background 0.18s ease;
}

.action-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.action-button.secondary {
  background: transparent;
  color: var(--text-primary);
}

.action-button:disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.result-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.result-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
}

.result-section {
  max-height: min(72vh, 760px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.result-scroll {
  min-height: 120px;
}

.result-user {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.result-meta {
  min-width: 0;
}

.result-meta p {
  margin-top: 6px;
  word-break: break-word;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  border: 1px dashed var(--border-primary);
  border-radius: 16px;
  background: var(--surface-primary);
}

.card-scroll::-webkit-scrollbar {
  width: 6px;
}

.card-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: var(--border-primary);
}

@media (max-width: 1100px) {
  .toolbar-card,
  .friends-main {
    grid-template-columns: minmax(0, 1fr);
  }

  .toolbar-meta {
    justify-content: flex-start;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .friends-page {
    padding: 14px;
  }

  .toolbar-card,
  .content-card {
    padding: 16px;
    border-radius: 20px;
  }

  .request-card,
  .result-card {
    border-radius: 16px;
  }

  .toolbar-form {
    grid-template-columns: 1fr;
  }

  .request-card {
    grid-template-columns: 1fr;
  }

  .request-row {
    grid-template-columns: 1fr;
  }

  .request-actions,
  .result-footer,
  .result-actions,
  .user-row,
  .section-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .status-chip,
  .section-count {
    align-self: flex-start;
  }
}
</style>
