<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <div class="theme-switch" role="group" aria-label="主题切换">
      <span :class="['theme-thumb', `theme-thumb-${theme}`]"></span>
      <button
        class="theme-option"
        :class="{ active: theme === 'dark' }"
        type="button"
        aria-label="夜间模式"
        @click="setTheme('dark')"
      >
        <i class="fa-solid fa-moon"></i>
      </button>
      <button
        class="theme-option"
        :class="{ active: theme === 'light' }"
        type="button"
        aria-label="亮色模式"
        @click="setTheme('light')"
      >
        <i class="fa-solid fa-sun"></i>
      </button>
    </div>

    <AuthView
      v-if="!isAuthenticated"
      :busy="bootstrapping"
      @authenticated="handleAuthenticated"
    />

    <div v-else :class="['workspace', { 'workspace-collapsed': sidebarCollapsed }]">
      <Sidebar
        :user="user"
        :active-section="activeSection"
        :conversation-count="displayConversations.length"
        :contact-count="pendingIncomingRequestCount"
        :chat-unread-count="chatUnreadCount"
        :collapsed="sidebarCollapsed"
        @change-section="handleSectionChange"
        @toggle-collapse="toggleSidebar"
        @logout="logout"
      />

      <section class="workspace-panel">
        <header class="workspace-header">
          <h1>{{ headerTitle }}</h1>
        </header>

        <div v-if="errorMessage" class="banner banner-error">
          {{ errorMessage }}
        </div>

        <div
          :class="[
            'workspace-content',
            {
              'workspace-content-single': activeSection !== 'chats',
              'workspace-content-profile-open':
                activeSection === 'chats' && friendProfileOpen
            }
          ]"
        >
          <ChatSidebar
            v-if="activeSection === 'chats'"
            :conversations="displayConversations"
            :selected-conversation-id="selectedConversationId"
            :loading="bootstrapping"
            @select="handleConversationSelect"
          />

          <FriendList
            v-else-if="activeSection === 'contacts'"
            :users="displayDiscoverUsers"
            :incoming-requests="incomingFriendRequests"
            :outgoing-requests="outgoingFriendRequests"
            :loading="discoverLoading"
            @search="handleDiscoverSearch"
            @add-friend="handleAddFriend"
            @open-chat="handleOpenChat"
            @accept-request="handleAcceptFriendRequest"
            @reject-request="handleRejectFriendRequest"
            @remove-friend="handleRemoveFriend"
          />

          <ProfilePanel
            v-else
            :user="user"
            :saving="profileSaving"
            :uploading-avatar="avatarUploading"
            @save="handleProfileSave"
            @upload-avatar="handleAvatarUpload"
          />

          <ChatWindow
            v-if="activeSection === 'chats'"
            :conversation="selectedConversation"
            :messages="activeMessages"
            :current-user-id="user.id"
            :loading="loadingMessages"
            @send="handleSendMessage"
            @toggle-profile="toggleFriendProfile"
          />

          <FriendProfileCard
            v-if="activeSection === 'chats' && friendProfileOpen"
            :friend="activeFriendProfile"
            :saving-remark="friendProfileSaving"
            @save-remark="handleSaveFriendRemark"
            @remove-friend="handleRemoveSelectedFriend"
            @close="friendProfileOpen = false"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import AuthView from './views/AuthView.vue';
import Sidebar from './components/Sidebar.vue';
import ChatSidebar from './components/ChatSidebar.vue';
import FriendList from './components/FriendList.vue';
import ChatWindow from './components/ChatWindow.vue';
import FriendProfileCard from './components/FriendProfileCard.vue';
import ProfilePanel from './components/ProfilePanel.vue';
import request, { buildWebSocketUrl, getErrorMessage } from './utils/request';

const THEME_STORAGE_KEY = 'chat-theme';
const SIDEBAR_STORAGE_KEY = 'chat-sidebar-collapsed';

const getInitialTheme = () => {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  if (savedTheme === 'light' || savedTheme === 'dark') {
    return savedTheme;
  }
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
};

const getInitialSidebarState = () =>
  localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1';

const isAuthenticated = ref(Boolean(localStorage.getItem('token')));
const bootstrapping = ref(false);
const loadingMessages = ref(false);
const profileSaving = ref(false);
const avatarUploading = ref(false);
const discoverLoading = ref(false);
const errorMessage = ref('');
const theme = ref(getInitialTheme());
const sidebarCollapsed = ref(getInitialSidebarState());
const friendProfileSaving = ref(false);
const friendProfileOpen = ref(false);

const user = ref({
  id: '',
  userName: '',
  avatarUrl: '/images/avatar-default.png',
  telephone: '',
  bio: ''
});

const activeSection = ref('chats');
const conversations = ref([]);
const discoverUsers = ref([]);
const friendRequests = ref([]);
const activeFriendProfile = ref(null);
const selectedConversationId = ref('');
const messageMap = ref({});
const unreadMap = ref({});
const discoverKeyword = ref('');

const websocketRef = ref(null);
const reconnectTimer = ref(null);
const allowReconnect = ref(true);

const selectedConversation = computed(
  () =>
    conversations.value.find(
      (conversation) => conversation.id === selectedConversationId.value
    ) || null
);

const displayConversations = computed(() =>
  conversations.value.map((conversation) => ({
    ...conversation,
    unreadCount: unreadMap.value[conversation.id] || 0
  }))
);

const incomingFriendRequests = computed(() =>
  friendRequests.value.filter((item) => item.direction === 'incoming')
);

const outgoingFriendRequests = computed(() =>
  friendRequests.value.filter((item) => item.direction === 'outgoing')
);

const pendingIncomingRequestCount = computed(
  () => incomingFriendRequests.value.filter((item) => item.status === 'pending').length
);

const displayDiscoverUsers = computed(() => {
  const incomingMap = new Map(
    incomingFriendRequests.value
      .filter((item) => item.status === 'pending')
      .map((item) => [item.user.id, item])
  );
  const outgoingMap = new Map(
    outgoingFriendRequests.value
      .filter((item) => item.status === 'pending')
      .map((item) => [item.user.id, item])
  );

  return discoverUsers.value.map((userItem) => ({
    ...userItem,
    incomingRequest: incomingMap.get(userItem.id) || null,
    outgoingRequest: outgoingMap.get(userItem.id) || null
  }));
});

const activeMessages = computed(
  () => messageMap.value[selectedConversationId.value] || []
);

const chatUnreadCount = computed(() =>
  Object.values(unreadMap.value).reduce((total, count) => total + count, 0)
);

const headerTitle = computed(() => {
  if (activeSection.value === 'contacts') {
    return '添加好友';
  }

  if (activeSection.value === 'profile') {
    return '个人中心';
  }

  return selectedConversation.value?.title || '消息';
});

const applyTheme = (nextTheme) => {
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
};

const setTheme = (nextTheme) => {
  theme.value = nextTheme;
};

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebarCollapsed.value ? '1' : '0');
};

watch(
  theme,
  (nextTheme) => {
    applyTheme(nextTheme);
  },
  { immediate: true }
);

const setError = (message = '') => {
  errorMessage.value = message;
};

const markUserAsFriend = (friendId) => {
  discoverUsers.value = discoverUsers.value.map((item) =>
    item.id === friendId ? { ...item, isFriend: true } : item
  );
};

const unmarkUserAsFriend = (friendId) => {
  discoverUsers.value = discoverUsers.value.map((item) =>
    item.id === friendId ? { ...item, isFriend: false } : item
  );
};

const upsertFriendRequest = (requestItem) => {
  const nextItems = friendRequests.value.filter((item) => item.id !== requestItem.id);
  friendRequests.value = [requestItem, ...nextItems].sort(
    (left, right) =>
      new Date(right.updatedAt || right.createdAt).getTime() -
      new Date(left.updatedAt || left.createdAt).getTime()
  );
};

const removeFriendLocally = (friendId) => {
  unmarkUserAsFriend(friendId);
  conversations.value = conversations.value.filter(
    (conversation) => conversation.participantId !== friendId
  );
  discoverUsers.value = discoverUsers.value.map((item) =>
    item.id === friendId ? { ...item, remark: '' } : item
  );
  if (activeFriendProfile.value?.id === friendId) {
    activeFriendProfile.value = null;
    friendProfileOpen.value = false;
  }

  const activeConversation = conversations.value.find(
    (conversation) => conversation.id === selectedConversationId.value
  );
  if (!activeConversation) {
    selectedConversationId.value = conversations.value[0]?.id || '';
  }
};

const sortConversations = (items) =>
  [...items].sort(
    (left, right) =>
      new Date(right.updatedAt || 0).getTime() -
      new Date(left.updatedAt || 0).getTime()
  );

const upsertConversation = (conversation) => {
  const existing = conversations.value.find((item) => item.id === conversation.id);
  const merged = existing ? { ...existing, ...conversation } : conversation;
  const next = conversations.value.filter((item) => item.id !== conversation.id);
  conversations.value = sortConversations([merged, ...next]);
};

const appendMessageToCache = (conversationId, message) => {
  const existingMessages = messageMap.value[conversationId] || [];
  if (existingMessages.some((item) => item.id === message.id)) {
    return;
  }

  messageMap.value = {
    ...messageMap.value,
    [conversationId]: [...existingMessages, message].sort(
      (left, right) =>
        new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime()
    )
  };
};

const resetUnread = (conversationId) => {
  if (!unreadMap.value[conversationId]) {
    return;
  }

  const nextMap = { ...unreadMap.value };
  delete nextMap[conversationId];
  unreadMap.value = nextMap;
};

const increaseUnread = (conversationId) => {
  unreadMap.value = {
    ...unreadMap.value,
    [conversationId]: (unreadMap.value[conversationId] || 0) + 1
  };
};

const applyProfileLocally = (profile) => {
  user.value = {
    ...user.value,
    ...profile
  };

  const nextMessageMap = {};
  for (const [conversationId, messages] of Object.entries(messageMap.value)) {
    nextMessageMap[conversationId] = messages.map((message) =>
      message.senderId === profile.id
        ? {
            ...message,
            senderName: profile.userName,
            senderAvatar: profile.avatarUrl
          }
        : message
    );
  }
  messageMap.value = nextMessageMap;
};

const syncConversationEvent = ({ conversation, message }) => {
  if (conversation) {
    upsertConversation(conversation);
    if (!selectedConversationId.value) {
      selectedConversationId.value = conversation.id;
    }
  }

  if (conversation && message) {
    appendMessageToCache(conversation.id, message);
  }
};

const applyWorkspacePayload = ({ profile, conversations: nextConversations }) => {
  user.value = profile;
  conversations.value = sortConversations(nextConversations);

  if (
    !selectedConversationId.value ||
    !nextConversations.some(
      (conversation) => conversation.id === selectedConversationId.value
    )
  ) {
    selectedConversationId.value = nextConversations[0]?.id || '';
  }
};

const loadMessages = async (conversationId) => {
  if (!conversationId) {
    return;
  }

  loadingMessages.value = true;

  try {
    const response = await request.get(`/conversations/${conversationId}/messages`);
    messageMap.value = {
      ...messageMap.value,
      [conversationId]: response.data
    };
    resetUnread(conversationId);
  } catch (error) {
    setError(getErrorMessage(error));
  } finally {
    loadingMessages.value = false;
  }
};

const loadFriendProfile = async (friendId) => {
  if (!friendId) {
    activeFriendProfile.value = null;
    friendProfileOpen.value = false;
    return;
  }

  try {
    const response = await request.get(`/friends/${friendId}`);
    activeFriendProfile.value = response.data;
  } catch (error) {
    activeFriendProfile.value = null;
    setError(getErrorMessage(error));
  }
};

const loadWorkspace = async () => {
  bootstrapping.value = true;
  setError('');

  try {
    const [profileResponse, conversationsResponse, friendRequestsResponse] = await Promise.all([
      request.get('/auth/me'),
      request.get('/conversations'),
      request.get('/friend-requests')
    ]);

    applyWorkspacePayload({
      profile: profileResponse.data,
      conversations: conversationsResponse.data
    });
    friendRequests.value = friendRequestsResponse.data;

    if (selectedConversationId.value) {
      await loadMessages(selectedConversationId.value);
    }
  } catch (error) {
    closeWebSocket(true);
    localStorage.removeItem('token');
    isAuthenticated.value = false;
    setError(getErrorMessage(error));
  } finally {
    bootstrapping.value = false;
  }
};

const clearReconnectTimer = () => {
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value);
    reconnectTimer.value = null;
  }
};

const scheduleReconnect = () => {
  if (!allowReconnect.value || !isAuthenticated.value) {
    return;
  }

  clearReconnectTimer();
  reconnectTimer.value = setTimeout(() => {
    connectWebSocket();
  }, 1500);
};

const handleSocketMessage = (event) => {
  let payload;

  try {
    payload = JSON.parse(event.data);
  } catch {
    return;
  }

  if (payload.type === 'error') {
    setError(payload.message || '实时连接失败');
    return;
  }

  if (payload.type === 'profile.updated') {
    applyProfileLocally(payload.profile);
    return;
  }

  if (payload.type === 'friend.request.created' || payload.type === 'friend.request.updated') {
    if (payload.request?.status === 'accepted') {
      markUserAsFriend(payload.request.user.id);
    }
    upsertFriendRequest(payload.request);
    return;
  }

  if (payload.type === 'friend.removed') {
    removeFriendLocally(payload.friendId);
    return;
  }

  if (payload.type === 'friend.profile.updated') {
    const friend = payload.friend;
    if (activeFriendProfile.value?.id === friend.id) {
      activeFriendProfile.value = friend;
    }
    conversations.value = conversations.value.map((conversation) =>
      conversation.participantId === friend.id
        ? {
            ...conversation,
            title: friend.remark || friend.userName,
            remark: friend.remark || ''
          }
        : conversation
    );
    discoverUsers.value = discoverUsers.value.map((item) =>
      item.id === friend.id ? { ...item, remark: friend.remark || '' } : item
    );
    return;
  }

  if (payload.type === 'conversation.created' || payload.type === 'conversation.updated') {
    syncConversationEvent({ conversation: payload.conversation });
    return;
  }

  if (payload.type === 'message.created') {
    syncConversationEvent({
      conversation: payload.conversation,
      message: payload.message
    });

    const isIncoming = payload.message?.senderId && payload.message.senderId !== user.value.id;
    const isCurrentConversation =
      activeSection.value === 'chats' &&
      selectedConversationId.value === payload.conversation?.id &&
      !document.hidden;

    if (isIncoming && !isCurrentConversation) {
      increaseUnread(payload.conversation.id);
    }
  }
};

function closeWebSocket(manual = false) {
  allowReconnect.value = !manual;
  clearReconnectTimer();

  if (websocketRef.value) {
    const socket = websocketRef.value;
    websocketRef.value = null;
    socket.onopen = null;
    socket.onmessage = null;
    socket.onclose = null;
    socket.onerror = null;
    socket.close();
  }
}

function connectWebSocket() {
  const token = localStorage.getItem('token');
  if (!token || !isAuthenticated.value) {
    return;
  }

  closeWebSocket(false);
  allowReconnect.value = true;

  const socket = new WebSocket(buildWebSocketUrl(token));
  websocketRef.value = socket;

  socket.onopen = () => {
    clearReconnectTimer();
  };

  socket.onmessage = handleSocketMessage;

  socket.onerror = () => {};

  socket.onclose = () => {
    if (websocketRef.value === socket) {
      websocketRef.value = null;
    }
    scheduleReconnect();
  };
}

const handleAuthenticated = async ({ token }) => {
  localStorage.setItem('token', token);
  isAuthenticated.value = true;
  selectedConversationId.value = '';
  messageMap.value = {};
  unreadMap.value = {};
  discoverUsers.value = [];
  friendRequests.value = [];
  connectWebSocket();
  await loadWorkspace();
};

const handleSectionChange = (section) => {
  activeSection.value = section;
};

const handleConversationSelect = async (conversationId) => {
  selectedConversationId.value = conversationId;
  activeSection.value = 'chats';
  resetUnread(conversationId);
  friendProfileOpen.value = false;
  const conversation = conversations.value.find((item) => item.id === conversationId);
  await loadFriendProfile(conversation?.participantId || '');

  if (!messageMap.value[conversationId]) {
    await loadMessages(conversationId);
  }
};

const handleDiscoverSearch = async (keyword) => {
  discoverKeyword.value = keyword;
  setError('');

  if (!keyword.trim()) {
    discoverUsers.value = [];
    return;
  }

  discoverLoading.value = true;

  try {
    const response = await request.get('/users/discover', {
      params: { q: keyword.trim() }
    });
    discoverUsers.value = response.data;
  } catch (error) {
    setError(getErrorMessage(error));
  } finally {
    discoverLoading.value = false;
  }
};

const handleAddFriend = async ({ friendId, message }) => {
  setError('');

  try {
    const response = await request.post('/friends', { friendId, message });
    upsertFriendRequest(response.data);
  } catch (error) {
    setError(getErrorMessage(error));
  }
};

const handleAcceptFriendRequest = async (requestId) => {
  setError('');

  try {
    const response = await request.post(`/friend-requests/${requestId}/accept`);
    markUserAsFriend(response.data.request.user.id);
    upsertFriendRequest(response.data.request);
    syncConversationEvent({ conversation: response.data.conversation });
  } catch (error) {
    setError(getErrorMessage(error));
  }
};

const handleRejectFriendRequest = async (requestId) => {
  setError('');

  try {
    const response = await request.post(`/friend-requests/${requestId}/reject`);
    upsertFriendRequest(response.data);
  } catch (error) {
    setError(getErrorMessage(error));
  }
};

const handleOpenChat = async (friendId) => {
  const existingConversation = conversations.value.find(
    (conversation) => conversation.participantId === friendId
  );

  if (!existingConversation) {
    setError('对方同意好友申请后才能开始聊天。');
    return;
  }

  selectedConversationId.value = existingConversation.id;
  activeSection.value = 'chats';
  resetUnread(existingConversation.id);
  friendProfileOpen.value = false;
  await loadFriendProfile(friendId);

  if (!messageMap.value[existingConversation.id]) {
    await loadMessages(existingConversation.id);
  }
};

const handleRemoveFriend = async (friendId) => {
  setError('');

  try {
    await request.delete(`/friends/${friendId}`);
    removeFriendLocally(friendId);
  } catch (error) {
    setError(getErrorMessage(error));
  }
};

const handleRemoveSelectedFriend = async () => {
  if (!activeFriendProfile.value?.id) {
    return;
  }
  await handleRemoveFriend(activeFriendProfile.value.id);
};

const toggleFriendProfile = () => {
  if (!selectedConversation.value?.participantId) {
    return;
  }
  friendProfileOpen.value = !friendProfileOpen.value;
};

const handleSaveFriendRemark = async (remark) => {
  if (!activeFriendProfile.value?.id) {
    return;
  }

  friendProfileSaving.value = true;
  setError('');

  try {
    const response = await request.put(`/friends/${activeFriendProfile.value.id}/remark`, {
      remark
    });
    activeFriendProfile.value = response.data;
    conversations.value = conversations.value.map((conversation) =>
      conversation.participantId === response.data.id
        ? {
            ...conversation,
            title: response.data.remark || response.data.userName,
            remark: response.data.remark || ''
          }
        : conversation
    );
    discoverUsers.value = discoverUsers.value.map((item) =>
      item.id === response.data.id ? { ...item, remark: response.data.remark || '' } : item
    );
  } catch (error) {
    setError(getErrorMessage(error));
  } finally {
    friendProfileSaving.value = false;
  }
};

const handleSendMessage = async (content) => {
  if (!selectedConversationId.value) {
    return;
  }

  setError('');

  try {
    const response = await request.post(
      `/conversations/${selectedConversationId.value}/messages`,
      { content }
    );

    syncConversationEvent(response.data);
  } catch (error) {
    setError(getErrorMessage(error));
  }
};

const handleProfileSave = async (payload) => {
  profileSaving.value = true;
  setError('');

  try {
    const response = await request.put('/profile', payload);
    applyProfileLocally(response.data);
  } catch (error) {
    setError(getErrorMessage(error));
  } finally {
    profileSaving.value = false;
  }
};

const handleAvatarUpload = async (file) => {
  avatarUploading.value = true;
  setError('');

  try {
    const formData = new FormData();
    formData.append('avatar', file);
    const response = await request.post('/profile/avatar', formData);
    applyProfileLocally(response.data);
  } catch (error) {
    setError(getErrorMessage(error));
    throw error;
  } finally {
    avatarUploading.value = false;
  }
};

const logout = () => {
  closeWebSocket(true);
  localStorage.removeItem('token');
  isAuthenticated.value = false;
  user.value = {
    id: '',
    userName: '',
    avatarUrl: '/images/avatar-default.png',
    telephone: '',
    bio: ''
  };
  conversations.value = [];
  discoverUsers.value = [];
  friendRequests.value = [];
  activeFriendProfile.value = null;
  friendProfileOpen.value = false;
  selectedConversationId.value = '';
  messageMap.value = {};
  unreadMap.value = {};
  discoverKeyword.value = '';
  setError('');
};

onMounted(async () => {
  if (isAuthenticated.value) {
    connectWebSocket();
    await loadWorkspace();
    if (selectedConversation.value?.participantId) {
      await loadFriendProfile(selectedConversation.value.participantId);
    }
  }
});

onBeforeUnmount(() => {
  closeWebSocket(true);
});
</script>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(40px);
  opacity: 0.55;
  pointer-events: none;
}

.ambient-left {
  top: -4%;
  left: -90px;
  width: 280px;
  height: 280px;
  background: var(--page-orb-1);
}

.ambient-right {
  right: -110px;
  bottom: 0;
  width: 320px;
  height: 320px;
  background: var(--page-orb-2);
}

.theme-switch {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 3;
  display: inline-grid;
  grid-template-columns: repeat(2, 44px);
  align-items: center;
  padding: 4px;
  border: 1px solid var(--border-primary);
  border-radius: 999px;
  background: var(--surface-primary);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(16px);
  isolation: isolate;
}

.theme-thumb {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 44px;
  height: calc(100% - 8px);
  border-radius: 999px;
  background: var(--accent);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
  transition:
    transform 0.24s ease,
    background 0.24s ease;
  z-index: 0;
}

.theme-thumb-light {
  transform: translateX(44px);
}

.theme-option {
  position: relative;
  z-index: 1;
  width: 44px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: var(--text-tertiary);
  font-size: 0.92rem;
  transition:
    color 0.22s ease,
    transform 0.22s ease;
}

.theme-option.active {
  color: var(--accent-contrast);
}

.theme-option:not(.active):hover {
  color: var(--text-primary);
}

.theme-option.active i {
  transform: scale(1.04);
}

.workspace {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  min-height: 100vh;
  height: 100vh;
  padding: 18px;
  gap: 14px;
}

.workspace-collapsed {
  grid-template-columns: 84px minmax(0, 1fr);
}

.workspace-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--border-primary);
  border-radius: 28px;
  background: var(--surface-primary);
  box-shadow: var(--shadow-panel);
  backdrop-filter: blur(16px);
}

.workspace-header {
  padding: 18px 22px 14px;
  border-bottom: 1px solid var(--border-secondary);
}

.workspace-header h1 {
  color: var(--text-primary);
  font-size: 0.98rem;
  line-height: 1.2;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.workspace-content {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.workspace-content-profile-open {
  grid-template-columns: 300px minmax(0, 1fr) 280px;
}

.workspace-content-single {
  grid-template-columns: 1fr;
}

.banner {
  margin: 12px 20px 0;
  padding: 11px 12px;
  border-radius: 14px;
  font-size: 0.8rem;
}

.banner-error {
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  color: var(--danger-text);
}

@media (max-width: 1100px) {
  .workspace,
  .workspace-collapsed {
    grid-template-columns: 84px minmax(0, 1fr);
  }

  .workspace-content {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .workspace-content-profile-open {
    grid-template-columns: 280px minmax(0, 1fr) 260px;
  }
}

@media (max-width: 980px) {
  .theme-switch {
    top: 12px;
    right: 12px;
  }

  .workspace,
  .workspace-collapsed {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 100vh;
    padding-top: 64px;
  }

  .workspace-panel {
    min-height: calc(100vh - 82px);
  }

  .workspace-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .workspace,
  .workspace-collapsed {
    padding: 60px 10px 10px;
    gap: 10px;
  }

  .workspace-panel {
    min-height: calc(100vh - 70px);
    border-radius: 22px;
  }

  .workspace-header {
    padding: 14px 16px 12px;
  }
}
</style>
