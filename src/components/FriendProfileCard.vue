<template>
  <aside class="friend-profile-card">
    <div v-if="friend" class="profile-shell">
      <header class="profile-header">
        <span class="profile-label">Contact</span>
        <button class="close-button" type="button" @click="$emit('close')">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>

      <section class="profile-hero">
        <img :src="friend.avatarUrl" :alt="friend.userName" class="friend-avatar" />
        <div class="hero-copy">
          <strong>{{ friend.remark || friend.userName }}</strong>
          <span v-if="friend.remark" class="hero-secondary">{{ friend.userName }}</span>
          <span class="hero-secondary">{{ friend.telephone }}</span>
        </div>
      </section>

      <section class="glass-card">
        <div class="card-top">
          <span>备注</span>
          <small>{{ remarkDraft.length }}/20</small>
        </div>
        <div class="remark-wrap">
          <input
            v-model.trim="remarkDraft"
            class="remark-input"
            type="text"
            maxlength="20"
            placeholder="设置备注"
          />
          <button
            class="save-button"
            type="button"
            :disabled="savingRemark"
            @click="$emit('save-remark', remarkDraft)"
          >
            {{ savingRemark ? '保存中' : '保存' }}
          </button>
        </div>
      </section>

      <section class="glass-card info-card">
        <div class="info-row">
          <span>简介</span>
          <p>{{ friend.bio || '这个好友还没有填写个人简介。' }}</p>
        </div>
        <div class="divider"></div>
        <div class="info-row">
          <span>成为好友</span>
          <p>{{ formatTime(friend.friendedAt) || '未知' }}</p>
        </div>
      </section>

      <button class="danger-button" type="button" @click="$emit('remove-friend')">
        删除好友
      </button>
    </div>

    <div v-else class="friend-empty">当前没有可查看的好友资料</div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  friend: {
    type: Object,
    default: null
  },
  savingRemark: {
    type: Boolean,
    default: false
  }
});

defineEmits(['save-remark', 'remove-friend', 'close']);

const remarkDraft = ref('');

watch(
  () => props.friend,
  (value) => {
    remarkDraft.value = value?.remark || '';
  },
  { immediate: true, deep: true }
);

const formatTime = (value) => {
  if (!value) {
    return '';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value));
};
</script>

<style scoped>
.friend-profile-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 22px 18px 18px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0) 18%),
    var(--surface-tertiary);
  overflow-y: auto;
  backdrop-filter: blur(18px);
}

.profile-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profile-label {
  color: var(--text-tertiary);
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.close-button {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
  backdrop-filter: blur(10px);
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    color 0.18s ease;
}

.close-button:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.14);
  color: var(--text-primary);
}

.profile-hero {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 4px 0 2px;
}

.friend-avatar {
  width: 72px;
  height: 72px;
  border-radius: 26px;
  object-fit: cover;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.12);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.hero-copy strong {
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.2;
}

.hero-secondary,
.friend-empty,
.card-top small,
.info-row p,
.info-row span {
  color: var(--text-secondary);
  font-size: 0.74rem;
  line-height: 1.55;
}

.hero-secondary {
  color: var(--text-tertiary);
}

.glass-card {
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.05);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 10px 30px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(18px);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.card-top span {
  color: var(--text-primary);
  font-size: 0.76rem;
  font-weight: 600;
}

.remark-wrap {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.remark-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary);
  font-size: 0.76rem;
}

.remark-input::placeholder {
  color: var(--text-tertiary);
}

.remark-input:focus {
  outline: 1px solid rgba(255, 255, 255, 0.24);
}

.save-button,
.danger-button {
  height: 40px;
  padding: 0 14px;
  border-radius: 14px;
  font-size: 0.74rem;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease;
}

.save-button {
  background: rgba(255, 255, 255, 0.92);
  color: #111;
}

.save-button:hover:not(:disabled),
.danger-button:hover {
  transform: translateY(-1px);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.info-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: grid;
  gap: 4px;
}

.info-row span {
  color: var(--text-tertiary);
}

.info-row p {
  margin: 0;
  color: var(--text-primary);
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
}

.danger-button {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: var(--danger-text);
}

.friend-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

@media (max-width: 1100px) {
  .friend-profile-card {
    border-left: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
}

@media (max-width: 640px) {
  .friend-profile-card {
    padding: 16px 14px 14px;
  }

  .remark-wrap {
    grid-template-columns: 1fr;
  }
}
</style>
