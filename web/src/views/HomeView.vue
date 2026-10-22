<template>
  <main class="page">
    <div class="container">
      <section class="hero">
        <div class="hero-text">
          <h1>拍照识病，科学防治</h1>
          <p>
            上传农作物叶片照片，系统基于深度学习模型自动识别 38 类常见病害，
            并给出针对性的农药 / 物理 / 农业防治方案与防治效果判断标准。
          </p>
          <div class="hero-stats">
            <div class="stat card"><strong>{{ stats.classes }}</strong><span>类病害覆盖</span></div>
            <div class="stat card"><strong>99.28%</strong><span>模型测试准确率</span></div>
            <div class="stat card"><strong>{{ stats.treatments || '90+' }}</strong><span>条防治方案</span></div>
            <div class="stat card"><strong>{{ stats.faqs }}</strong><span>条专家问答</span></div>
          </div>
        </div>
      </section>

      <section class="recognize card">
        <h2 class="section-title">开始识别</h2>
        <p class="section-sub">请上传叶片正面清晰照片，尽量包含病斑区域，识别效果更佳</p>
        <UploadBox :preview-url="previewUrl" :file="file" @select="onSelect" />
        <div v-if="error" class="error-box">{{ error }}</div>
        <div class="actions">
          <button class="btn" :disabled="!file || loading" @click="submit">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '识别中…' : '开始识别' }}
          </button>
          <span v-if="loading" class="muted">模型推理中，通常 1 秒内完成</span>
        </div>
      </section>

      <section class="features">
        <h2 class="section-title">系统功能</h2>
        <p class="section-sub">识别 → 防治 → 咨询，一站式病害防治解决方案</p>
        <div class="grid feature-grid">
          <div v-for="f in features" :key="f.title" class="card feature" @click="$router.push(f.to)">
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
            <span class="feature-link">进入 →</span>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import UploadBox from '../components/UploadBox.vue'
import { getHealth, predictImage } from '../api'
import { store } from '../store'

const router = useRouter()
const file = ref(null)
const previewUrl = ref('')
const loading = ref(false)
const error = ref('')
const stats = ref({ classes: 38, faqs: 36, treatments: null })

const features = [
  { title: '图像识别', desc: 'ResNet18 迁移学习 + ONNX Runtime，上传即得病害类别与置信度', to: '/' },
  { title: '防治推荐', desc: '按农药 / 物理 / 农业三类给出方案，附带预期效果与见效时间', to: '/knowledge' },
  { title: '专家咨询', desc: '常见问题智能问答，未匹配可留言等待回复', to: '/consult' }
]

onMounted(async () => {
  try {
    stats.value = await getHealth()
  } catch {
    /* 后端未启动时展示默认值 */
  }
})

function onSelect(f) {
  error.value = ''
  if (!f) {
    file.value = null
    previewUrl.value = ''
    return
  }
  if (!f.type.startsWith('image/')) {
    error.value = '请选择图片文件（JPG / PNG / BMP / WEBP）'
    return
  }
  if (f.size > 10 * 1024 * 1024) {
    error.value = '图片超过 10 MB 限制，请压缩后重试'
    return
  }
  file.value = f
  previewUrl.value = URL.createObjectURL(f)
}

async function submit() {
  if (!file.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await predictImage(file.value)
    store.setResult(result, previewUrl.value)
    router.push('/result')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hero {
  padding: 18px 0 26px;
}

.hero-text h1 {
  margin: 0 0 10px;
  font-size: 34px;
  color: var(--green-900);
  letter-spacing: 1px;
}

.hero-text p {
  max-width: 720px;
  margin: 0 0 22px;
  color: var(--ink-2);
  font-size: 16px;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 10px;
}

.stat strong {
  font-size: 22px;
  color: var(--green-700);
}

.stat span {
  font-size: 12.5px;
  color: var(--ink-3);
}

.recognize {
  padding: 24px;
  margin-bottom: 30px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}

.features {
  margin-bottom: 20px;
}

.feature-grid {
  grid-template-columns: repeat(3, 1fr);
}

.feature {
  padding: 20px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
}

.feature:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.feature h3 {
  margin: 0 0 8px;
  color: var(--green-900);
}

.feature p {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--ink-2);
}

.feature-link {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--green-700);
}

@media (max-width: 860px) {
  .hero-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
