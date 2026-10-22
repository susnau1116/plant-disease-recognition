<template>
  <main class="page">
    <div class="container">
      <button class="back" @click="$router.push('/knowledge')">← 返回知识库</button>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中…</div>
      <div v-else-if="error" class="error-box">{{ error }}</div>
      <template v-else-if="disease">
        <header class="d-head card">
          <div>
            <div class="d-tags">
              <span class="tag tag-blue">{{ disease.crop }}</span>
              <span :class="['tag', disease.healthy ? 'tag-green' : 'tag-red']">
                {{ disease.healthy ? '健康' : '病害' }}
              </span>
            </div>
            <h1>{{ disease.name_cn }}</h1>
            <p class="muted">{{ disease.name_en }} · {{ disease.class_name }}</p>
          </div>
          <button class="btn btn-ghost" @click="$router.push('/consult')">咨询专家</button>
        </header>

        <ExampleGallery
          :images="disease.examples || []"
          :title="disease.healthy ? '健康叶片例图' : '病害例图'"
        />

        <section class="card info">
          <h2 class="section-title">{{ disease.healthy ? '状态说明' : '病害信息' }}</h2>
          <div class="info-grid">
            <div><h4>症状表现</h4><p>{{ disease.symptoms || '—' }}</p></div>
            <div><h4>发病规律</h4><p>{{ disease.occurrence || '—' }}</p></div>
            <div><h4>传播途径</h4><p>{{ disease.transmission || '—' }}</p></div>
          </div>
        </section>

        <section class="treatments">
          <h2 class="section-title">{{ disease.healthy ? '栽培与预防建议' : '防治方案' }}</h2>
          <p class="section-sub">含预期效果、见效时间、效果判断标准与未达预期处理</p>
          <div class="grid treat-grid">
            <TreatmentCard v-for="(t, i) in disease.treatments" :key="i" :treatment="t" />
          </div>
        </section>
      </template>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ExampleGallery from '../components/ExampleGallery.vue'
import TreatmentCard from '../components/TreatmentCard.vue'
import { getDisease } from '../api'

const route = useRoute()
const disease = ref(null)
const loading = ref(false)
const error = ref('')

async function load(className) {
  loading.value = true
  error.value = ''
  disease.value = null
  try {
    disease.value = await getDisease(className)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => load(route.params.className))
watch(() => route.params.className, (v) => v && load(v))
</script>

<style scoped>
.back {
  border: none;
  background: none;
  color: var(--green-700);
  font-size: 14.5px;
  padding: 0;
  margin-bottom: 14px;
}

.d-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px;
  margin-bottom: 18px;
}

.d-head h1 {
  margin: 10px 0 4px;
  font-size: 26px;
  color: var(--green-900);
}

.d-head p {
  margin: 0;
  font-size: 13px;
}

.d-tags {
  display: flex;
  gap: 8px;
}

.info {
  padding: 22px;
  margin-bottom: 22px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.info-grid h4 {
  margin: 0 0 6px;
  color: var(--green-700);
  font-size: 14.5px;
}

.info-grid p {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}

.treat-grid {
  grid-template-columns: repeat(2, 1fr);
}

@media (max-width: 900px) {
  .info-grid,
  .treat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
