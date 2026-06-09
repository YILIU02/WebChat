<template>
  <section class="auth-shell">
    <div class="auth-card">
      <div class="auth-head">
        <span class="auth-kicker">WebChat</span>
        <h1>{{ mode === 'login' ? '登录' : '注册' }}</h1>
      </div>

      <div class="tab-row">
        <button
          :class="['tab-button', { active: mode === 'login' }]"
          type="button"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          :class="['tab-button', { active: mode === 'register' }]"
          type="button"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <div v-if="notice" class="notice">{{ notice }}</div>
      <div v-if="errorMessage" class="notice notice-error">{{ errorMessage }}</div>

      <form v-if="mode === 'login'" class="auth-form" @submit.prevent="handleLogin">
        <label>
          <span>手机号</span>
          <div class="phone-row">
            <select v-model="loginForm.regionCode">
              <option v-for="region in regions" :key="region.code" :value="region.code">
                {{ region.country }} {{ region.code }}
              </option>
            </select>
            <input
              v-model.trim="loginForm.telephone"
              type="tel"
              placeholder="请输入手机号"
              autocomplete="username"
            />
          </div>
        </label>

        <label>
          <span>密码</span>
          <input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </label>

        <button class="submit-button" type="submit" :disabled="busy || submitting">
          {{ submitting ? '登录中...' : '登录' }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="handleRegister">
        <div class="register-avatar">
          <button class="avatar-picker" type="button" @click="openAvatarPicker">
            <img :src="registerAvatarPreview" alt="avatar preview" class="avatar-preview" />
            <span>上传头像</span>
          </button>
          <input
            ref="avatarInputRef"
            class="file-input"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            @change="handleAvatarChange"
          />
        </div>

        <label>
          <span>昵称</span>
          <input
            v-model.trim="registerForm.userName"
            type="text"
            placeholder="请输入昵称"
            autocomplete="nickname"
          />
        </label>

        <label>
          <span>手机号</span>
          <div class="phone-row">
            <select v-model="registerForm.regionCode">
              <option v-for="region in regions" :key="region.code" :value="region.code">
                {{ region.country }} {{ region.code }}
              </option>
            </select>
            <input
              v-model.trim="registerForm.telephone"
              type="tel"
              placeholder="请输入手机号"
              autocomplete="username"
            />
          </div>
        </label>

        <label>
          <span>验证码</span>
          <div class="code-row">
            <input
              v-model.trim="registerForm.verificationCode"
              type="text"
              maxlength="6"
              placeholder="请输入 6 位验证码"
            />
            <button
              class="code-button"
              type="button"
              :disabled="sendingCode || codeCountdown > 0"
              @click="handleSendCode"
            >
              {{
                sendingCode
                  ? '发送中...'
                  : codeCountdown > 0
                    ? `${codeCountdown}s`
                    : '获取验证码'
              }}
            </button>
          </div>
        </label>

        <label>
          <span>密码</span>
          <input
            v-model="registerForm.password"
            type="password"
            placeholder="8-32 位，需包含字母和数字"
            autocomplete="new-password"
          />
        </label>

        <label>
          <span>确认密码</span>
          <input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            autocomplete="new-password"
          />
        </label>

        <label>
          <span>个人简介</span>
          <textarea
            v-model.trim="registerForm.bio"
            rows="3"
            placeholder="选填，最多 120 字"
          ></textarea>
        </label>

        <button class="submit-button" type="submit" :disabled="busy || submitting">
          {{ submitting ? '注册中...' : '注册' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
import request, { getErrorMessage } from '../utils/request';

defineProps({
  busy: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['authenticated']);

const regions = [{ code: '+86', country: '中国' }];
const mode = ref('login');
const submitting = ref(false);
const sendingCode = ref(false);
const codeCountdown = ref(0);
const notice = ref('');
const errorMessage = ref('');
const avatarInputRef = ref(null);
const registerAvatarFile = ref(null);
const registerAvatarObjectUrl = ref('');

let countdownTimer = null;

const loginForm = ref({
  regionCode: '+86',
  telephone: '13800000001',
  password: 'Pass1234'
});

const createRegisterForm = () => ({
  regionCode: '+86',
  userName: '',
  telephone: '',
  verificationCode: '',
  password: '',
  confirmPassword: '',
  bio: ''
});

const registerForm = ref(createRegisterForm());

const registerAvatarPreview = computed(
  () => registerAvatarObjectUrl.value || '/images/avatar-default.png'
);

const resetMessages = () => {
  notice.value = '';
  errorMessage.value = '';
};

const revokeRegisterAvatarPreview = () => {
  if (registerAvatarObjectUrl.value) {
    URL.revokeObjectURL(registerAvatarObjectUrl.value);
    registerAvatarObjectUrl.value = '';
  }
};

const resetRegisterAvatar = () => {
  revokeRegisterAvatarPreview();
  registerAvatarFile.value = null;
  if (avatarInputRef.value) {
    avatarInputRef.value.value = '';
  }
};

const resetRegisterForm = () => {
  registerForm.value = createRegisterForm();
  resetRegisterAvatar();
};

const stopCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
};

const startCountdown = (seconds) => {
  stopCountdown();
  codeCountdown.value = seconds;
  countdownTimer = setInterval(() => {
    codeCountdown.value -= 1;
    if (codeCountdown.value <= 0) {
      stopCountdown();
      codeCountdown.value = 0;
    }
  }, 1000);
};

const switchMode = (nextMode) => {
  mode.value = nextMode;
  resetMessages();
};

const validatePhone = (telephone) => /^1[3-9]\d{9}$/.test(telephone);
const validatePassword = (password) =>
  /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d\W_]{8,32}$/.test(password);

const openAvatarPicker = () => {
  avatarInputRef.value?.click();
};

const handleAvatarChange = (event) => {
  const [file] = event.target.files || [];
  if (!file) {
    return;
  }

  revokeRegisterAvatarPreview();
  registerAvatarFile.value = file;
  registerAvatarObjectUrl.value = URL.createObjectURL(file);
};

const handleSendCode = async () => {
  resetMessages();

  if (!validatePhone(registerForm.value.telephone)) {
    errorMessage.value = '请输入有效的手机号。';
    return;
  }

  sendingCode.value = true;

  try {
    const response = await request.post('/auth/send-code', {
      regionCode: registerForm.value.regionCode,
      telephone: registerForm.value.telephone,
      purpose: 'register'
    });
    startCountdown(60);
    notice.value = response.data?.debugCode
      ? `验证码已发送，开发环境验证码：${response.data.debugCode}`
      : '验证码已发送，请注意查收。';
  } catch (error) {
    errorMessage.value = getErrorMessage(error);
  } finally {
    sendingCode.value = false;
  }
};

const handleLogin = async () => {
  resetMessages();

  if (!validatePhone(loginForm.value.telephone)) {
    errorMessage.value = '请输入有效的手机号。';
    return;
  }

  if (!loginForm.value.password) {
    errorMessage.value = '请输入密码。';
    return;
  }

  submitting.value = true;

  try {
    const response = await request.post('/auth/login', loginForm.value);
    emit('authenticated', response.data);
  } catch (error) {
    errorMessage.value = getErrorMessage(error);
  } finally {
    submitting.value = false;
  }
};

const handleRegister = async () => {
  resetMessages();

  if (registerForm.value.userName.length < 2 || registerForm.value.userName.length > 20) {
    errorMessage.value = '昵称长度需在 2 到 20 个字符之间。';
    return;
  }

  if (!validatePhone(registerForm.value.telephone)) {
    errorMessage.value = '请输入有效的手机号。';
    return;
  }

  if (!/^\d{6}$/.test(registerForm.value.verificationCode)) {
    errorMessage.value = '请输入 6 位验证码。';
    return;
  }

  if (!validatePassword(registerForm.value.password)) {
    errorMessage.value = '密码需为 8 到 32 位，并同时包含字母和数字。';
    return;
  }

  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致。';
    return;
  }

  if (registerForm.value.bio.length > 120) {
    errorMessage.value = '个人简介不能超过 120 个字符。';
    return;
  }

  submitting.value = true;

  try {
    const formData = new FormData();
    formData.append('regionCode', registerForm.value.regionCode);
    formData.append('userName', registerForm.value.userName);
    formData.append('telephone', registerForm.value.telephone);
    formData.append('verificationCode', registerForm.value.verificationCode);
    formData.append('password', registerForm.value.password);
    formData.append('bio', registerForm.value.bio);

    if (registerAvatarFile.value) {
      formData.append('avatar', registerAvatarFile.value);
    }

    await request.post('/auth/register', formData);
    notice.value = '注册成功，请直接登录。';
    loginForm.value.regionCode = registerForm.value.regionCode;
    loginForm.value.telephone = registerForm.value.telephone;
    loginForm.value.password = registerForm.value.password;
    resetRegisterForm();
    stopCountdown();
    codeCountdown.value = 0;
    mode.value = 'login';
  } catch (error) {
    errorMessage.value = getErrorMessage(error);
  } finally {
    submitting.value = false;
  }
};

onBeforeUnmount(() => {
  revokeRegisterAvatarPreview();
  stopCountdown();
});
</script>

<style scoped>
.auth-shell {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 28px;
}

.auth-card {
  width: min(100%, 430px);
  padding: 28px;
  border: 1px solid var(--border-primary);
  border-radius: 30px;
  background: var(--surface-primary);
  box-shadow: var(--shadow-panel);
  backdrop-filter: blur(18px);
}

.auth-head {
  margin-bottom: 18px;
}

.auth-kicker {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--surface-secondary);
  color: var(--text-secondary);
  font-size: 0.74rem;
}

.auth-head h1 {
  color: var(--text-primary);
  font-size: 1.32rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.tab-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}

.tab-button {
  height: 40px;
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  background: var(--surface-tertiary);
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
}

.tab-button.active {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-contrast);
}

.notice {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 14px;
  background: var(--success-soft);
  color: var(--text-primary);
  font-size: 0.8rem;
}

.notice-error {
  background: var(--danger-soft);
  color: var(--danger-text);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auth-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.auth-form input,
.auth-form textarea,
.auth-form select {
  width: 100%;
  padding: 12px 13px;
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 0.82rem;
}

.auth-form input::placeholder,
.auth-form textarea::placeholder {
  color: var(--text-tertiary);
}

.auth-form input:focus,
.auth-form textarea:focus,
.auth-form select:focus {
  outline: 1px solid var(--accent);
}

.phone-row,
.code-row {
  display: grid;
  gap: 8px;
}

.phone-row {
  grid-template-columns: 116px minmax(0, 1fr);
}

.code-row {
  grid-template-columns: minmax(0, 1fr) 112px;
}

.register-avatar {
  display: flex;
  justify-content: center;
  margin-bottom: 2px;
}

.avatar-picker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 6px 0 2px;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.avatar-preview {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  border: 1px solid var(--border-primary);
  object-fit: cover;
  background: var(--surface-secondary);
}

.file-input {
  display: none;
}

.code-button,
.submit-button {
  height: 42px;
  border-radius: 14px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.code-button {
  background: var(--surface-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-secondary);
}

.code-button:disabled,
.submit-button:disabled {
  opacity: 0.55;
  cursor: wait;
}

.submit-button {
  margin-top: 4px;
  background: var(--accent);
  color: var(--accent-contrast);
}
</style>
