<template>
  <aside :class="['sidebar', { collapsed }]">
    <button
      v-if="collapsed"
      class="collapse-toggle collapse-toggle-floating"
      type="button"
      title="展开侧边栏"
      @click.stop="$emit('toggle-collapse')"
    >
      <i class="fa-solid fa-angles-right"></i>
    </button>

    <div
      :class="['profile-card', { active: activeSection === 'profile', compact: collapsed }]"
      @click="$emit('change-section', 'profile')"
    >
      <img :src="user.avatarUrl" :alt="user.userName" class="profile-avatar" />

      <div v-if="!collapsed" class="profile-meta">
        <strong>{{ user.userName }}</strong>
        <span>{{ user.telephone }}</span>
      </div>

      <button
        v-if="!collapsed"
        class="collapse-toggle"
        type="button"
        title="收起侧边栏"
        @click.stop="$emit('toggle-collapse')"
      >
        <i class="fa-solid fa-angles-left"></i>
      </button>
    </div>

    <nav class="nav-list">
      <button
        v-for="item in navItems"
        :key="item.key"
        :class="['nav-item', { active: activeSection === item.key, compact: collapsed }]"
        :title="item.label"
        @click="$emit('change-section', item.key)"
      >
        <span class="nav-icon-wrap">
          <i :class="item.icon"></i>
          <span v-if="item.hasBadge" class="nav-badge dot"></span>
        </span>
        <span v-if="!collapsed">{{ item.label }}</span>
        <small v-if="!collapsed && item.count !== null">{{ item.count }}</small>
      </button>
    </nav>

    <button
      class="logout-button"
      :class="{ compact: collapsed }"
      :title="collapsed ? '退出登录' : ''"
      @click="$emit('logout')"
    >
      <i class="fa-solid fa-arrow-right-from-bracket"></i>
      <span v-if="!collapsed">退出登录</span>
    </button>
  </aside>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  user: {
    type: Object,
    required: true
  },
  activeSection: {
    type: String,
    required: true
  },
  conversationCount: {
    type: Number,
    default: 0
  },
  contactCount: {
    type: Number,
    default: 0
  },
  chatUnreadCount: {
    type: Number,
    default: 0
  },
  collapsed: {
    type: Boolean,
    default: false
  }
});

defineEmits(['change-section', 'toggle-collapse', 'logout']);

const navItems = computed(() => [
  {
    key: 'chats',
    label: '会话',
    count: props.conversationCount,
    hasBadge: props.chatUnreadCount > 0,
    icon: 'fa-solid fa-comments'
  },
  {
    key: 'contacts',
    label: '添加好友',
    count: null,
    hasBadge: props.contactCount > 0,
    icon: 'fa-solid fa-user-plus'
  },
  {
    key: 'profile',
    label: '个人中心',
    count: null,
    hasBadge: false,
    icon: 'fa-solid fa-user-gear'
  }
]);
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
  border: 1px solid var(--border-primary);
  border-radius: 28px;
  background: var(--surface-primary);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(16px);
}

.sidebar.collapsed {
  align-items: center;
}

.profile-card {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 40px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border-radius: 18px;
  background: var(--surface-secondary);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    border-color 0.18s ease;
}

.profile-card.active {
  border: 1px solid var(--border-primary);
}

.profile-card.compact {
  grid-template-columns: 44px;
  justify-content: center;
  gap: 0;
  width: auto;
  padding: 10px;
}

.profile-avatar {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  object-fit: cover;
  border: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.profile-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.profile-meta strong {
  font-size: 0.82rem;
  font-weight: 600;
}

.profile-meta span {
  color: var(--text-tertiary);
  font-size: 0.72rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapse-toggle {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: transparent;
  color: var(--text-tertiary);
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.collapse-toggle:hover {
  background: var(--surface-primary);
  color: var(--text-primary);
}

.collapse-toggle-floating {
  align-self: center;
  margin-bottom: -4px;
  background: var(--surface-secondary);
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.nav-item,
.logout-button {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 12px;
  border-radius: 14px;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
  font-size: 0.78rem;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.nav-item.compact,
.logout-button.compact {
  grid-template-columns: 1fr;
  justify-items: center;
  padding: 12px 0;
}

.nav-item:hover,
.logout-button:hover,
.profile-card:hover {
  background: var(--surface-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent);
  color: var(--accent-contrast);
}

.nav-icon-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.nav-badge {
  position: absolute;
  top: -4px;
  right: -5px;
  background: #ff4d4f;
  box-shadow: 0 0 0 2px var(--surface-primary);
}

.nav-badge.dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
}

.nav-item small {
  opacity: 0.75;
}

.logout-button {
  margin-top: auto;
  grid-template-columns: 18px 1fr;
}

@media (max-width: 980px) {
  .sidebar,
  .sidebar.collapsed {
    align-items: stretch;
  }

  .collapse-toggle-floating {
    display: none;
  }

  .profile-card,
  .profile-card.compact {
    grid-template-columns: 44px minmax(0, 1fr) 40px;
    width: 100%;
    gap: 12px;
    padding: 12px;
  }

  .nav-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .nav-item.compact,
  .logout-button.compact {
    grid-template-columns: 24px 1fr auto;
    justify-items: stretch;
    padding: 11px 12px;
  }
}
</style>
