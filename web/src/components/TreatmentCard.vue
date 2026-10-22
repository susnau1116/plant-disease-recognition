<template>
  <div class="treatment card">
    <div class="treatment-head">
      <span :class="['tag', typeTag]">{{ treatment.type }}</span>
      <h4 class="treatment-name">{{ treatment.name }}</h4>
    </div>
    <dl class="treatment-body">
      <div v-if="show('formulation')" class="row"><dt>剂型</dt><dd>{{ treatment.formulation }}</dd></div>
      <div v-if="show('dosage')" class="row"><dt>用量</dt><dd>{{ treatment.dosage }}</dd></div>
      <div v-if="show('usage')" class="row"><dt>使用方法</dt><dd>{{ treatment.usage }}</dd></div>
      <div v-if="show('precautions')" class="row"><dt>注意事项</dt><dd>{{ treatment.precautions }}</dd></div>
    </dl>
    <div class="effect">
      <div class="effect-title">防治效果</div>
      <div class="effect-grid">
        <div class="effect-item">
          <span class="effect-key">预期效果</span>
          <p>{{ treatment.expected_effect || '—' }}</p>
        </div>
        <div class="effect-item">
          <span class="effect-key">见效时间</span>
          <p>{{ treatment.effect_time || '—' }}</p>
        </div>
        <div class="effect-item">
          <span class="effect-key">效果判断标准</span>
          <p>{{ treatment.judgement || '—' }}</p>
        </div>
        <div class="effect-item">
          <span class="effect-key">未达预期处理</span>
          <p>{{ treatment.fallback || '—' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  treatment: { type: Object, required: true }
})

const typeTag = computed(() => {
  if (props.treatment.type?.includes('农药')) return 'tag-green'
  if (props.treatment.type?.includes('物理')) return 'tag-blue'
  return 'tag-amber'
})

function show(key) {
  const v = props.treatment[key]
  return v && v !== '—'
}
</script>

<style scoped>
.treatment {
  padding: 18px;
}

.treatment-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.treatment-name {
  margin: 0;
  font-size: 16px;
}

.treatment-body {
  margin: 0;
}

.row {
  display: flex;
  gap: 10px;
  font-size: 14px;
  padding: 5px 0;
}

.row dt {
  flex: 0 0 72px;
  color: var(--ink-3);
}

.row dd {
  margin: 0;
  color: var(--ink-2);
}

.effect {
  margin-top: 12px;
  border: 1px solid var(--green-100);
  background: var(--green-50);
  border-radius: 10px;
  padding: 12px 14px;
}

.effect-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--green-900);
  margin-bottom: 8px;
}

.effect-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 18px;
}

.effect-item p {
  margin: 2px 0 0;
  font-size: 13.5px;
  color: var(--ink-2);
}

.effect-key {
  font-size: 12px;
  color: var(--green-700);
  font-weight: 600;
}

@media (max-width: 720px) {
  .effect-grid {
    grid-template-columns: 1fr;
  }
}
</style>
