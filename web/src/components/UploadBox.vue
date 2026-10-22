<template>
  <div class="upload card" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="onDrop">
    <template v-if="!previewUrl">
      <div class="upload-zone" @click="pick">
        <div class="upload-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="currentColor" stroke-width="1.6">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <circle cx="9" cy="9" r="2.2" />
            <path d="M3.5 17l5-5 4 4 3-3 5 5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <p class="upload-title">点击选择或拖拽叶片图片到此处</p>
        <p class="muted">支持 JPG / PNG / BMP / WEBP，单张不超过 10 MB</p>
      </div>
    </template>
    <template v-else>
      <div class="preview">
        <img :src="previewUrl" alt="待识别图片" />
        <div class="preview-actions">
          <span class="muted">{{ file?.name }}</span>
          <button class="btn-ghost btn" type="button" @click="retake">重新选择</button>
        </div>
      </div>
    </template>
    <input ref="inputRef" type="file" accept="image/*" hidden @change="onChange" />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  previewUrl: { type: String, default: '' },
  file: { type: Object, default: null }
})
const emit = defineEmits(['select'])

const inputRef = ref(null)
const dragging = ref(false)

function pick() {
  inputRef.value?.click()
}

function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) emit('select', f)
}

function onChange(e) {
  const f = e.target.files?.[0]
  if (f) emit('select', f)
  e.target.value = ''
}

function retake() {
  emit('select', null)
  pick()
}
</script>

<style scoped>
.upload {
  padding: 14px;
  border-style: dashed;
  border-width: 2px;
  border-color: var(--line);
  transition: border-color 0.2s, background 0.2s;
}

.upload.dragging {
  border-color: var(--green-500);
  background: var(--green-100);
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 44px 20px;
  cursor: pointer;
  text-align: center;
}

.upload-icon {
  color: var(--green-500);
  margin-bottom: 8px;
}

.upload-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.preview img {
  display: block;
  width: 100%;
  max-height: 380px;
  object-fit: contain;
  border-radius: 10px;
  background: var(--green-50);
}

.preview-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}
</style>
