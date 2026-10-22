<template>
  <main class="page">
    <div class="container consult-layout">
      <aside class="side card">
        <h3>常见问题</h3>
        <div class="cats">
          <button :class="['chip', { active: !category }]" @click="selectCategory('')">全部</button>
          <button
            v-for="c in categories"
            :key="c"
            :class="['chip', { active: category === c }]"
            @click="selectCategory(c)"
          >
            {{ c }}
          </button>
        </div>
        <ul class="q-list">
          <li v-for="f in faqs" :key="f.id" @click="ask(f.question)">{{ f.question }}</li>
        </ul>
      </aside>

      <section class="chat card">
        <div class="chat-head">
          <h2>专家咨询</h2>
          <span class="muted">基于知识库的智能问答，未匹配可留言</span>
        </div>

        <div ref="listRef" class="chat-body">
          <div v-if="!messages.length" class="chat-empty">
            <p>您好，我是农作物病害防治助手。</p>
            <p class="muted">可以问我：“白粉病怎么防治”“叶背有白霉是什么病”，或直接点击左侧常见问题。</p>
          </div>
          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
            <div class="bubble">
              <p>{{ m.text }}</p>
              <template v-if="m.meta">
                <button
                  v-for="r in m.meta.related"
                  :key="r.id"
                  class="rel"
                  @click="ask(r.question)"
                >
                  相关问题：{{ r.question }}
                </button>
                <p v-if="m.meta.suggestion" class="suggest">{{ m.meta.suggestion }}</p>
                <button v-if="m.meta.suggestion" class="btn leave-btn" @click="openLeave(m.meta.question)">
                  留言提问
                </button>
              </template>
            </div>
          </div>
          <div v-if="thinking" class="msg system">
            <div class="bubble"><span class="spinner"></span> 正在查找答案…</div>
          </div>
        </div>

        <div class="chat-input">
          <textarea
            v-model.trim="question"
            rows="2"
            placeholder="请输入您的问题，如：番茄晚疫病怎么防治？"
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <button class="btn" :disabled="!question || thinking" @click="send">发送</button>
        </div>
      </section>
    </div>

    <div v-if="showLeave" class="modal-mask" @click.self="closeLeave">
      <div class="modal card">
        <h3>留言提问</h3>
        <p class="muted modal-sub">知识库未匹配的问题将转交工作人员，回复后可在「留言管理」查看。</p>
        <label class="field">
          <span>问题描述</span>
          <textarea
            v-model.trim="leaveQuestion"
            rows="3"
            maxlength="500"
            placeholder="请描述作物、症状与已采取的措施"
          ></textarea>
        </label>
        <label class="field">
          <span>联系方式（选填）</span>
          <input v-model.trim="leaveContact" maxlength="100" placeholder="手机号 / 邮箱 / 微信" />
        </label>
        <p v-if="leaveError" class="modal-error">{{ leaveError }}</p>
        <p v-if="leaveSuccess" class="modal-success">{{ leaveSuccess }}</p>
        <div class="modal-actions">
          <button class="btn" :disabled="!leaveQuestion || leaveSubmitting" @click="submitLeave">
            {{ leaveSubmitting ? '提交中…' : '提交留言' }}
          </button>
          <button class="btn btn-ghost" @click="closeLeave">关闭</button>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { consult, createMessage, getFaqs } from '../api'

const categories = ref([])
const faqs = ref([])
const category = ref('')
const question = ref('')
const messages = ref([])
const thinking = ref(false)
const listRef = ref(null)
const showLeave = ref(false)
const leaveQuestion = ref('')
const leaveContact = ref('')
const leaveError = ref('')
const leaveSuccess = ref('')
const leaveSubmitting = ref(false)

onMounted(() => loadFaqs())

async function loadFaqs() {
  try {
    const data = await getFaqs(category.value || undefined)
    categories.value = data.categories
    faqs.value = data.items.slice(0, 12)
  } catch {
    /* 忽略：页面仍可提问 */
  }
}

function selectCategory(c) {
  category.value = c
  loadFaqs()
}

async function ask(text) {
  question.value = text
  await send()
}

async function send() {
  const text = question.value
  if (!text || thinking.value) return
  messages.value.push({ role: 'user', text })
  question.value = ''
  thinking.value = true
  scrollToEnd()
  try {
    const data = await consult(text)
    const answerText = data.matched
      ? data.answer.answer
      : '知识库中暂未找到完全匹配的答案。'
    messages.value.push({
      role: 'system',
      text: data.matched ? `【${data.answer.category}】${data.answer.question}\n${answerText}` : answerText,
      meta: {
        related: data.related || [],
        suggestion: data.matched ? '' : data.suggestion,
        question: data.matched ? '' : text
      }
    })
  } catch (e) {
    messages.value.push({ role: 'system', text: e.message })
  } finally {
    thinking.value = false
    scrollToEnd()
  }
}

function scrollToEnd() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

function openLeave(question) {
  leaveQuestion.value = question || ''
  leaveContact.value = ''
  leaveError.value = ''
  leaveSuccess.value = ''
  showLeave.value = true
}

function closeLeave() {
  if (leaveSubmitting.value) return
  showLeave.value = false
}

async function submitLeave() {
  const text = leaveQuestion.value
  if (!text || leaveSubmitting.value) return
  leaveSubmitting.value = true
  leaveError.value = ''
  try {
    await createMessage(text, leaveContact.value)
    leaveSuccess.value = '留言已提交，我们会尽快回复。'
    leaveQuestion.value = ''
    leaveContact.value = ''
  } catch (e) {
    leaveError.value = e.message
  } finally {
    leaveSubmitting.value = false
  }
}
</script>

<style scoped>
.consult-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  align-items: start;
}

.side {
  padding: 18px;
  position: sticky;
  top: 88px;
}

.side h3 {
  margin: 0 0 12px;
}

.cats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.chip {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12.5px;
}

.chip.active {
  background: var(--green-700);
  border-color: var(--green-700);
  color: #fff;
}

.q-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.q-list li {
  padding: 9px 10px;
  border-radius: 8px;
  font-size: 13.5px;
  color: var(--ink-2);
  cursor: pointer;
}

.q-list li:hover {
  background: var(--green-100);
  color: var(--green-900);
}

.chat {
  display: flex;
  flex-direction: column;
  height: 640px;
  overflow: hidden;
}

.chat-head {
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
}

.chat-head h2 {
  margin: 0;
  font-size: 18px;
}

.chat-head span {
  font-size: 12.5px;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
  background: var(--green-50);
}

.chat-empty {
  color: var(--ink-2);
  font-size: 14.5px;
}

.msg {
  display: flex;
  margin-bottom: 14px;
}

.msg.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 78%;
  padding: 11px 15px;
  border-radius: 12px;
  font-size: 14.5px;
  background: #fff;
  border: 1px solid var(--line);
  white-space: pre-wrap;
}

.msg.user .bubble {
  background: var(--green-700);
  border-color: var(--green-700);
  color: #fff;
}

.bubble p {
  margin: 0;
}

.rel {
  display: block;
  margin-top: 8px;
  border: none;
  background: none;
  padding: 0;
  color: var(--green-700);
  font-size: 13px;
  text-align: left;
}

.rel:hover {
  text-decoration: underline;
}

.suggest {
  margin-top: 8px !important;
  font-size: 13px;
  color: var(--ink-3);
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--line);
  background: #fff;
}

.chat-input textarea {
  flex: 1;
  resize: none;
}

.leave-btn {
  margin-top: 10px;
  padding: 7px 16px;
  font-size: 13.5px;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(20, 40, 24, 0.45);
}

.modal {
  width: min(520px, 100%);
  padding: 22px 24px;
}

.modal h3 {
  margin: 0 0 6px;
}

.modal-sub {
  margin: 0 0 16px;
  font-size: 13px;
}

.field {
  display: block;
  margin-bottom: 14px;
}

.field span {
  display: block;
  margin-bottom: 6px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink-2);
}

.field textarea,
.field input {
  width: 100%;
  resize: vertical;
}

.modal-error {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--red-100);
  color: var(--red);
  font-size: 13.5px;
}

.modal-success {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--green-100);
  color: var(--green-900);
  font-size: 13.5px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .consult-layout {
    grid-template-columns: 1fr;
  }
  .side {
    position: static;
  }
}
</style>
