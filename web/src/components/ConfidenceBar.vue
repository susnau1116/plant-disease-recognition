<template>
  <div class="conf">
    <div class="conf-head">
      <span class="conf-label">{{ label }}</span>
      <span class="conf-value">{{ percent }}%</span>
    </div>
    <div class="conf-track">
      <div class="conf-fill" :style="{ width: percent + '%', background: color }"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: Number, required: true }
})

const percent = computed(() => (props.value * 100).toFixed(2))
const color = computed(() => {
  if (props.value >= 0.9) return 'var(--green-500)'
  if (props.value >= 0.6) return 'var(--amber)'
  return '#e57373'
})
</script>

<style scoped>
.conf-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  margin-bottom: 4px;
}

.conf-label {
  color: var(--ink-2);
}

.conf-value {
  font-weight: 700;
}

.conf-track {
  height: 8px;
  border-radius: 999px;
  background: var(--green-100);
  overflow: hidden;
}

.conf-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}
</style>
