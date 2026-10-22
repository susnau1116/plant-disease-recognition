<template>
  <main class="page">
    <div class="container">
      <div class="page-head">
        <div>
          <h2 class="section-title">留言管理</h2>
          <p class="section-sub">查看用户留言并回复，回复后移动端「我的留言」可见。</p>
        </div>
        <button class="btn btn-ghost" @click="load">刷新</button>
      </div>

      <div class="filters">
        <button
          v-for="f in filters"
          :key="f.value"
          :class="['chip', { active: status === f.value }]"
          @click="selectStatus(f.value)"
        >
          {{ f.label }}
        </button>
        <span class="muted total">共 {{ total }} 条</span>
      </div>

      <div v-if="loading" class="loading"><span class="spinner"></span>加载中…</div>
      <div v-else-if="error" class="error-box">{{ error }}</div>
      <div v-else-if="!items.length" class="card empty muted">暂无留言</div>

      <article v-for="m in items" :key="m.id" class="card item">
        <header class="item-head">
          <div class="item-meta">
            <strong>#{{ m.id }}</strong>
            <span :class="['tag', m.status === 'replied' ? 'tag-green' : 'tag-amber']">
              {{ m.status === 'replied' ? '已回复' : '待回复' }}
            </span>
            <span class="muted time">{{ m.created_at }}</span>
          </div>
          <span v-if="m.contact" class="muted contact">联系方式：{{ m.contact }}</span>
        </header>

        <p class="question">{{ m.question }}</p>

        <div v-if="m.reply" class="reply">
          <span class="reply-label">回复</span>
          <p>{{ m.reply }}</p>
          <span class="muted time">{{ m.replied_at }}</span>
        </div>

        <div class="reply-form">
          <textarea
            v-model.trim="drafts[m.id]"
            rows="2"
            maxlength="1000"
            :placeholder="m.reply ? '修改回复内容' : '输入回复内容'"
          ></textarea>
          <button
            class="btn"
            :disabled="!drafts[m.id] || replyingId === m.id"
            @click="submitReply(m)"
          >
            {{ replyingId === m.id ? '提交中…' : m.reply ? '更新回复' : '回复' }}
          </button>
        </div>
        <p v-if="errors[m.id]" class="reply-error">{{ errors[m.id] }}</p>
      </article>
    </div>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getMessages, replyMessage } from '../api'

const filters = [
  { label: '全部', value: '' },
  { label: '待回复', value: 'pending' },
  { label: '已回复', value: 'replied' }
]

const status = ref('')
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const drafts = reactive({})
const errors = reactive({})
const replyingId = ref(null)

onMounted(load)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getMessages({ status: status.value || undefined })
    items.value = data.items
    total.value = data.total
    for (const m of data.items) {
      if (drafts[m.id] === undefined) drafts[m.id] = m.reply || ''
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function selectStatus(value) {
  status.value = value
  load()
}

async function submitReply(m) {
  const text = (drafts[m.id] || '').trim()
  if (!text || replyingId.value) return
  replyingId.value = m.id
  delete errors[m.id]
  try {
    const updated = await replyMessage(m.id, text)
    Object.assign(m, updated)
    drafts[m.id] = updated.reply || ''
    await load()
  } catch (e) {
    errors[m.id] = e.message
  } finally {
    replyingId.value = null
  }
}
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 13px;
}

.chip.active {
  background: var(--green-700);
  border-color: var(--green-700);
  color: #fff;
}

.total {
  margin-left: auto;
  font-size: 13px;
}

.empty {
  padding: 32px;
  text-align: center;
}

.item {
  padding: 18px 20px;
  margin-bottom: 14px;
}

.item-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.time {
  font-size: 12.5px;
}

.contact {
  font-size: 13px;
}

.question {
  margin: 12px 0;
  font-size: 15px;
  font-weight: 600;
  white-space: pre-wrap;
}

.reply {
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--green-50);
}

.reply-label {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--green-700);
}

.reply p {
  margin: 4px 0 6px;
  font-size: 14px;
  white-space: pre-wrap;
}

.reply-form {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-top: 10px;
}

.reply-form textarea {
  flex: 1;
  resize: vertical;
}

.reply-form .btn {
  padding: 9px 18px;
  font-size: 14px;
}

.reply-error {
  margin: 8px 0 0;
  color: var(--red);
  font-size: 13px;
}
</style>
