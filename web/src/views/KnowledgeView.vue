<template>
  <main class="page">
    <div class="container">
      <h1 class="page-title">病害知识库</h1>
      <p class="section-sub">覆盖 14 种作物、38 个类别，支持按作物筛选与关键词检索</p>

      <div class="toolbar card">
        <input v-model.trim="keyword" type="search" placeholder="搜索病害名称、症状关键词，如：晚疫病、白粉、霉层" @keyup.enter="search" />
        <button class="btn" @click="search">搜索</button>
      </div>

      <div class="crops">
        <button :class="['chip', { active: !crop }]" @click="selectCrop('')">全部作物</button>
        <button
          v-for="c in crops"
          :key="c.crop"
          :class="['chip', { active: crop === c.crop }]"
          @click="selectCrop(c.crop)"
        >
          {{ c.crop }} ({{ c.total }})
        </button>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中…</div>
      <div v-else-if="error" class="error-box">{{ error }}</div>
      <template v-else>
        <p class="muted result-count">共 {{ total }} 条结果</p>
        <div class="grid list-grid">
          <DiseaseCard v-for="d in items" :key="d.class_name" :disease="d" />
        </div>
        <div v-if="total > pageSize" class="pager">
          <button class="btn btn-ghost" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ totalPages }} 页</span>
          <button class="btn btn-ghost" :disabled="page >= totalPages" @click="go(page + 1)">下一页</button>
        </div>
      </template>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import DiseaseCard from '../components/DiseaseCard.vue'
import { getCrops, getDiseases } from '../api'

const crops = ref([])
const keyword = ref('')
const crop = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const items = ref([])
const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

onMounted(async () => {
  try {
    crops.value = await getCrops()
  } catch {
    crops.value = []
  }
  fetchList()
})

async function fetchList() {
  loading.value = true
  error.value = ''
  try {
    const data = await getDiseases({
      page: page.value,
      page_size: pageSize,
      q: keyword.value || undefined,
      crop: crop.value || undefined
    })
    total.value = data.total
    items.value = data.items
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  fetchList()
}

function selectCrop(value) {
  crop.value = value
  page.value = 1
  fetchList()
}

function go(p) {
  page.value = p
  fetchList()
}
</script>

<style scoped>
.page-title {
  margin: 0 0 4px;
  font-size: 26px;
  color: var(--green-900);
}

.toolbar {
  display: flex;
  gap: 12px;
  padding: 14px;
  margin: 18px 0 14px;
}

.toolbar input {
  flex: 1;
}

.crops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 13.5px;
  transition: all 0.15s;
}

.chip:hover {
  border-color: var(--green-500);
  color: var(--green-700);
}

.chip.active {
  background: var(--green-700);
  border-color: var(--green-700);
  color: #fff;
}

.result-count {
  font-size: 13.5px;
  margin: 0 0 12px;
}

.list-grid {
  grid-template-columns: repeat(3, 1fr);
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 22px;
  font-size: 14px;
}

@media (max-width: 900px) {
  .list-grid {
    grid-template-columns: 1fr;
  }
}
</style>
