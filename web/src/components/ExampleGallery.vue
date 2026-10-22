<template>
  <section v-if="images.length" class="gallery card">
    <h2 class="section-title">{{ title }}</h2>
    <p class="section-sub">{{ subtitle }}</p>
    <div class="shots">
      <button
        v-for="(img, i) in images"
        :key="img"
        type="button"
        class="shot"
        @click="preview = img"
      >
        <img :src="img" :alt="`${title} ${i + 1}`" loading="lazy" />
      </button>
    </div>

    <div v-if="preview" class="lightbox" @click="preview = ''">
      <img :src="preview" :alt="title" />
      <span class="lightbox-hint">点击任意处关闭</span>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  images: { type: Array, default: () => [] },
  title: { type: String, default: '参考例图' },
  subtitle: { type: String, default: '来自 PlantVillage 数据集的典型样本，点击可放大对照' }
})

const preview = ref('')
</script>

<style scoped>
.gallery {
  padding: 22px;
  margin-bottom: 22px;
}

.shots {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.shot {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0;
  overflow: hidden;
  background: var(--green-50);
  transition: transform 0.15s, box-shadow 0.15s;
}

.shot:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.shot img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.lightbox {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(15, 28, 18, 0.82);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  cursor: zoom-out;
}

.lightbox img {
  max-width: min(88vw, 720px);
  max-height: 80vh;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}

.lightbox-hint {
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
}

@media (max-width: 720px) {
  .shots {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
