<template>
  <section class="profile-panel">
    <div class="profile-card">
      <div class="profile-header">
        <div
          class="avatar-dropzone"
          :class="{
            dragging: dragOver,
            uploading: uploadingAvatar
          }"
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="handleDrop"
          @click="openFilePicker"
        >
          <img :src="previewAvatarUrl" :alt="form.userName" class="profile-avatar" />
          <div class="avatar-overlay">
            <i class="fa-solid fa-camera"></i>
            <span>{{ uploadingAvatar ? '上传中...' : '拖拽或点击上传' }}</span>
          </div>
        </div>

        <input
          ref="fileInputRef"
          class="file-input"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          @change="handleFileInput"
        />

        <div class="profile-summary">
          <h2>{{ form.userName || '未命名用户' }}</h2>
          <p>{{ user.telephone }}</p>
          <small>支持 PNG / JPG / WEBP / GIF，自动压缩后上传</small>
        </div>
      </div>
    </div>

    <form class="profile-form" @submit.prevent="submit">
      <label>
        <span>昵称</span>
        <input v-model.trim="form.userName" type="text" />
      </label>

      <label class="profile-bio">
        <span>个人简介</span>
        <textarea v-model.trim="form.bio" rows="4"></textarea>
      </label>

      <div class="profile-actions">
        <button type="submit" :disabled="saving || uploadingAvatar">
          {{ saving ? '保存中...' : '保存资料' }}
        </button>
      </div>
    </form>

    <div v-if="cropperVisible" class="cropper-mask" @click.self="closeCropper">
      <div class="cropper-dialog">
        <div class="cropper-head">
          <h3>调整头像</h3>
          <button type="button" class="icon-button" @click="closeCropper">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="cropper-stage">
          <img
            ref="cropImageRef"
            :src="cropSourceUrl"
            class="crop-image"
            :style="cropImageStyle"
            @load="syncImageMetrics"
            @mousedown.prevent="startDrag"
          />
        </div>

        <div class="cropper-controls">
          <label>
            <span>缩放</span>
            <input
              v-model="zoom"
              type="range"
              min="1"
              max="3"
              step="0.01"
              @input="syncImageMetrics"
            />
          </label>
        </div>

        <div class="cropper-actions">
          <button type="button" class="ghost-button" @click="closeCropper">取消</button>
          <button type="button" class="primary-button" @click="confirmCrop">
            使用头像
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';

const props = defineProps({
  user: {
    type: Object,
    required: true
  },
  saving: {
    type: Boolean,
    default: false
  },
  uploadingAvatar: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['save', 'upload-avatar']);

const form = reactive({
  userName: '',
  bio: ''
});

const fileInputRef = ref(null);
const cropImageRef = ref(null);
const dragOver = ref(false);
const localPreviewUrl = ref('');
const cropperVisible = ref(false);
const cropSourceUrl = ref('');
const selectedFileName = ref('avatar.png');
const zoom = ref(1.2);
const cropPosition = reactive({ x: 0, y: 0 });
const imageMetrics = reactive({ width: 0, height: 0 });

let dragState = null;

watch(
  () => props.user,
  (value) => {
    form.userName = value.userName || '';
    form.bio = value.bio || '';
    localPreviewUrl.value = '';
  },
  { immediate: true, deep: true }
);

const previewAvatarUrl = computed(
  () => localPreviewUrl.value || props.user.avatarUrl || '/images/avatar-default.png'
);

const cropImageStyle = computed(() => ({
  transform: `translate(${cropPosition.x}px, ${cropPosition.y}px) scale(${zoom.value})`
}));

const openFilePicker = () => {
  fileInputRef.value?.click();
};

const revokeLocalPreview = () => {
  if (localPreviewUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(localPreviewUrl.value);
  }
};

const resetCropState = () => {
  cropPosition.x = 0;
  cropPosition.y = 0;
  zoom.value = 1.2;
  imageMetrics.width = 0;
  imageMetrics.height = 0;
};

const closeCropper = () => {
  cropperVisible.value = false;
  if (cropSourceUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(cropSourceUrl.value);
  }
  cropSourceUrl.value = '';
  resetCropState();
};

const syncImageMetrics = () => {
  const image = cropImageRef.value;
  if (!image) {
    return;
  }

  imageMetrics.width = image.naturalWidth;
  imageMetrics.height = image.naturalHeight;
};

const openCropper = (file) => {
  closeCropper();
  cropSourceUrl.value = URL.createObjectURL(file);
  selectedFileName.value = file.name || 'avatar.png';
  cropperVisible.value = true;
};

const readFileFromEvent = (event) => {
  const [file] = event.target.files || [];
  if (!file) {
    return;
  }
  openCropper(file);
  event.target.value = '';
};

const handleFileInput = (event) => {
  readFileFromEvent(event);
};

const handleDrop = (event) => {
  dragOver.value = false;
  const [file] = event.dataTransfer?.files || [];
  if (!file) {
    return;
  }
  openCropper(file);
};

const startDrag = (event) => {
  dragState = {
    startX: event.clientX,
    startY: event.clientY,
    originX: cropPosition.x,
    originY: cropPosition.y
  };
  window.addEventListener('mousemove', onDragging);
  window.addEventListener('mouseup', stopDrag);
};

const onDragging = (event) => {
  if (!dragState) {
    return;
  }
  cropPosition.x = dragState.originX + (event.clientX - dragState.startX);
  cropPosition.y = dragState.originY + (event.clientY - dragState.startY);
};

const stopDrag = () => {
  dragState = null;
  window.removeEventListener('mousemove', onDragging);
  window.removeEventListener('mouseup', stopDrag);
};

const loadImage = (url) =>
  new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = url;
  });

const createCroppedBlob = async () => {
  const image = await loadImage(cropSourceUrl.value);
  const canvas = document.createElement('canvas');
  const size = 512;
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext('2d');

  const scaledWidth = image.width * zoom.value;
  const scaledHeight = image.height * zoom.value;
  const drawX = cropPosition.x - (scaledWidth - size) / 2;
  const drawY = cropPosition.y - (scaledHeight - size) / 2;

  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, size, size);
  context.drawImage(image, drawX, drawY, scaledWidth, scaledHeight);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.86);
  });
};

const createUploadFile = async () => {
  const blob = await createCroppedBlob();
  return new File([blob], selectedFileName.value.replace(/\.\w+$/, '.jpg'), {
    type: 'image/jpeg'
  });
};

const confirmCrop = async () => {
  try {
    const uploadFile = await createUploadFile();
    const previewUrl = URL.createObjectURL(uploadFile);
    revokeLocalPreview();
    localPreviewUrl.value = previewUrl;
    await emit('upload-avatar', uploadFile);
    closeCropper();
  } catch (error) {
    revokeLocalPreview();
    localPreviewUrl.value = '';
  }
};

const submit = () => {
  emit('save', {
    userName: form.userName,
    avatarUrl: props.user.avatarUrl,
    bio: form.bio
  });
};

onBeforeUnmount(() => {
  stopDrag();
  revokeLocalPreview();
  closeCropper();
});
</script>

<style scoped>
.profile-panel {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  padding: 18px;
  min-height: 0;
  overflow-y: auto;
}

.profile-card,
.profile-form {
  border: 1px solid var(--border-secondary);
  border-radius: 20px;
  background: var(--surface-tertiary);
}

.profile-card {
  padding: 16px;
}

.profile-header {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.avatar-dropzone {
  position: relative;
  width: 116px;
  height: 116px;
  border-radius: 28px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid var(--border-primary);
  background: var(--surface-secondary);
}

.avatar-dropzone.dragging {
  outline: 2px solid var(--accent);
}

.avatar-dropzone.uploading {
  opacity: 0.7;
}

.profile-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(0, 0, 0, 0.38);
  color: #fff;
  font-size: 0.72rem;
  opacity: 0;
  transition: opacity 0.18s ease;
}

.avatar-dropzone:hover .avatar-overlay,
.avatar-dropzone.dragging .avatar-overlay {
  opacity: 1;
}

.file-input {
  display: none;
}

.profile-summary h2 {
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
}

.profile-summary p {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 0.76rem;
}

.profile-summary small {
  display: block;
  margin-top: 10px;
  color: var(--text-tertiary);
  font-size: 0.72rem;
  line-height: 1.5;
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.profile-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.profile-form input,
.profile-form textarea {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--border-secondary);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 0.8rem;
}

.profile-form input:focus,
.profile-form textarea:focus {
  outline: 1px solid var(--accent);
}

.profile-bio {
  flex: 1;
}

.profile-bio textarea {
  min-height: 148px;
  resize: vertical;
}

.profile-actions {
  display: flex;
  justify-content: flex-end;
}

.profile-actions button,
.primary-button,
.ghost-button {
  height: 40px;
  padding: 0 16px;
  border-radius: 14px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.profile-actions button,
.primary-button {
  background: var(--accent);
  color: var(--accent-contrast);
}

.profile-actions button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.ghost-button {
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-primary);
}

.cropper-mask {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
}

.cropper-dialog {
  width: min(92vw, 520px);
  padding: 18px;
  border: 1px solid var(--border-primary);
  border-radius: 24px;
  background: var(--surface-primary);
  box-shadow: var(--shadow-panel);
}

.cropper-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.cropper-head h3 {
  color: var(--text-primary);
  font-size: 0.94rem;
}

.icon-button {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--surface-secondary);
  color: var(--text-primary);
}

.cropper-stage {
  position: relative;
  overflow: hidden;
  width: min(72vw, 320px);
  height: min(72vw, 320px);
  margin: 0 auto;
  border-radius: 24px;
  background:
    linear-gradient(45deg, rgba(255, 255, 255, 0.05) 25%, transparent 25%),
    linear-gradient(-45deg, rgba(255, 255, 255, 0.05) 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, rgba(255, 255, 255, 0.05) 75%),
    linear-gradient(-45deg, transparent 75%, rgba(255, 255, 255, 0.05) 75%);
  background-size: 24px 24px;
  background-position: 0 0, 0 12px, 12px -12px, -12px 0;
}

.crop-image {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: none;
  max-height: none;
  transform-origin: center center;
  cursor: grab;
}

.cropper-controls {
  margin-top: 16px;
}

.cropper-controls label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.78rem;
}

.cropper-controls input[type='range'] {
  width: 100%;
}

.cropper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

@media (max-width: 980px) {
  .profile-panel {
    grid-template-columns: 1fr;
  }

  .profile-header {
    flex-direction: row;
    align-items: center;
  }
}

@media (max-width: 640px) {
  .profile-panel {
    padding: 12px;
    gap: 12px;
  }

  .profile-card,
  .profile-form {
    padding: 14px;
  }

  .profile-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
