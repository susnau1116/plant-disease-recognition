<template>
  <main class="page">
    <div class="container">
      <template v-if="result">
        <div class="result-head">
          <h1>识别结果</h1>
          <span class="muted">推理耗时 {{ result.inference_ms }} ms</span>
        </div>

        <div class="result-top">
          <div class="result-image card">
            <img v-if="store.lastImageUrl" :src="store.lastImageUrl" alt="识别图片" />
            <div class="image-info">
              <span class="tag tag-blue">{{ result.crop }}</span>
              <span :class="['tag', result.healthy ? 'tag-green' : 'tag-red']">
                {{ result.healthy ? '健康' : '病害' }}
              </span>
            </div>
          </div>

          <div class="result-main card">
            <div class="main-name">
              <h2>{{ result.name_cn }}</h2>
              <p class="muted">{{ result.disease.name_en }}</p>
            </div>
            <ConfidenceBar :label="'置信度 · ' + result.name_cn" :value="result.confidence" />

            <div class="topk">
              <h3>其他可能</h3>
              <ConfidenceBar
                v-for="item in otherTopK"
                :key="item.class_name"
                :label="item.name_cn"
                :value="item.confidence"
              />
            </div>

            <div class="main-actions">
              <button class="btn" @click="$router.push('/')">再识别一张</button>
              <button class="btn btn-ghost" @click="$router.push('/consult')">咨询专家</button>
            </div>
          </div>
        </div>

        <section class="detail card">
          <h2 class="section-title">{{ result.healthy ? '状态说明' : '病害信息' }}</h2>
          <div class="detail-grid">
            <div><h4>症状表现</h4><p>{{ result.disease.symptoms || '—' }}</p></div>
            <div><h4>发病规律</h4><p>{{ result.disease.occurrence || '—' }}</p></div>
            <div><h4>传播途径</h4><p>{{ result.disease.transmission || '—' }}</p></div>
          </div>
        </section>

        <ExampleGallery
          :images="result.disease.examples || []"
          :title="result.healthy ? '健康叶片参考例图' : '病害参考例图'"
          subtitle="与上传图片对照，辅助确认识别结果"
        />

        <section class="treatments">
          <h2 class="section-title">{{ result.healthy ? '栽培与预防建议' : '防治方案' }}</h2>
          <p class="section-sub">按农药 / 物理 / 农业防治分类，含预期效果、见效时间与效果判断标准</p>
          <div class="grid treat-grid">
            <TreatmentCard v-for="(t, i) in result.disease.treatments" :key="i" :treatment="t" />
          </div>
        </section>
      </template>

      <div v-else class="empty card">
        <h2>暂无识别结果</h2>
        <p class="muted">请先在首页上传叶片图片进行识别</p>
        <button class="btn" @click="$router.push('/')">去识别</button>
      </div>
    </div>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import ConfidenceBar from '../components/ConfidenceBar.vue'
import ExampleGallery from '../components/ExampleGallery.vue'
import TreatmentCard from '../components/TreatmentCard.vue'
import { store } from '../store'

const result = computed(() => store.lastResult)
const otherTopK = computed(() => (store.lastResult?.top_k || []).slice(1))
</script>

<style scoped>
.result-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 18px;
}

.result-head h1 {
  margin: 0;
  font-size: 26px;
  color: var(--green-900);
}

.result-top {
  display: grid;
  grid-template-columns: minmax(280px, 5fr) 7fr;
  gap: 18px;
  margin-bottom: 22px;
}

.result-image {
  padding: 14px;
}

.result-image img {
  display: block;
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  border-radius: 10px;
  background: var(--green-50);
}

.image-info {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.result-main {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.main-name h2 {
  margin: 0 0 2px;
  font-size: 24px;
  color: var(--green-900);
}

.main-name p {
  margin: 0;
  font-size: 13.5px;
}

.topk h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--ink-3);
  font-weight: 600;
}

.topk > :deep(.conf) + :deep(.conf) {
  margin-top: 10px;
}

.main-actions {
  display: flex;
  gap: 12px;
  margin-top: auto;
}

.detail {
  padding: 22px;
  margin-bottom: 22px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.detail-grid h4 {
  margin: 0 0 6px;
  color: var(--green-700);
  font-size: 14.5px;
}

.detail-grid p {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}

.treat-grid {
  grid-template-columns: repeat(2, 1fr);
}

.empty {
  padding: 60px 24px;
  text-align: center;
}

.empty h2 {
  margin: 0 0 6px;
}

.empty .btn {
  margin-top: 18px;
}

@media (max-width: 900px) {
  .result-top {
    grid-template-columns: 1fr;
  }
  .detail-grid,
  .treat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
