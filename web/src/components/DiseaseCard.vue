<template>
  <article class="dcard card" @click="$router.push(`/knowledge/${encodeURIComponent(disease.class_name)}`)">
    <div class="dcard-head">
      <h4>{{ disease.name_cn }}</h4>
      <span :class="['tag', disease.healthy ? 'tag-green' : 'tag-red']">
        {{ disease.healthy ? '健康' : '病害' }}
      </span>
    </div>
    <div class="dcard-meta">
      <span class="tag tag-blue">{{ disease.crop }}</span>
      <span class="muted">{{ disease.name_en }}</span>
    </div>
    <p class="dcard-symptom">{{ disease.symptoms }}</p>
  </article>
</template>

<script setup>
defineProps({
  disease: { type: Object, required: true }
})
</script>

<style scoped>
.dcard {
  padding: 16px 18px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
}

.dcard:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.dcard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.dcard-head h4 {
  margin: 0;
  font-size: 16px;
}

.dcard-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
  font-size: 12.5px;
}

.dcard-symptom {
  margin: 0;
  font-size: 13.5px;
  color: var(--ink-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
