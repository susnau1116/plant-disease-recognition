<template>
  <view class="page">
    <scroll-view class="cats" scroll-x>
      <view class="cats-inner">
        <text :class="['chip', { active: !category }]" @click="selectCategory('')">全部</text>
        <text
          v-for="c in categories"
          :key="c"
          :class="['chip', { active: category === c }]"
          @click="selectCategory(c)"
        >
          {{ c }}
        </text>
      </view>
    </scroll-view>

    <view class="card hot">
      <view class="hot-head">
        <text class="hot-title">常见问题（点击直接提问）</text>
        <text class="hot-link" @tap="goMessages">我的留言 ›</text>
      </view>
      <text v-for="f in faqs" :key="f.id" class="hot-item" @click="ask(f.question)">{{ f.question }}</text>
    </view>

    <scroll-view class="chat" scroll-y :scroll-into-view="lastId">
      <view v-if="!messages.length" class="chat-empty">
        <text>您好，我是农作物病害防治助手。</text>
        <text class="muted">可以问我：“白粉病怎么防治”“叶背有白霉是什么病”，也可以点击上方常见问题。</text>
      </view>
      <view v-for="(m, i) in messages" :id="'msg-' + i" :key="i" :class="['msg', m.role]">
        <view class="bubble">
          <text class="bubble-text">{{ m.text }}</text>
          <template v-if="m.meta">
            <text
              v-for="r in m.meta.related"
              :key="r.id"
              class="rel"
              @click="ask(r.question)"
            >相关问题：{{ r.question }}</text>
            <text v-if="m.meta.suggestion" class="suggest">{{ m.meta.suggestion }}</text>
          </template>
        </view>
      </view>
      <view v-if="thinking" id="msg-thinking" class="msg system">
        <view class="bubble"><text class="bubble-text">正在查找答案…</text></view>
      </view>
    </scroll-view>

    <view class="leave-bar card" @tap="goLeave(lastUnmatched)">
      <text class="leave-bar-text">未找到答案？可留言给工作人员</text>
      <view class="leave" hover-class="leave-hover">
        <text>留言提问 ›</text>
      </view>
    </view>

    <view class="input-bar card">
      <input
        v-model="question"
        placeholder="请输入您的问题"
        confirm-type="send"
        @confirm="send"
      />
      <text class="send" :class="{ disabled: !question || thinking }" @click="send">发送</text>
    </view>
  </view>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { consult, getFaqs } from '../../api'

const categories = ref([])
const faqs = ref([])
const category = ref('')
const question = ref('')
const messages = ref([])
const thinking = ref(false)
const lastId = ref('')
const lastUnmatched = ref('')

onMounted(() => loadFaqs())

async function loadFaqs() {
  try {
    const data = await getFaqs(category.value || undefined)
    categories.value = data.categories
    faqs.value = data.items.slice(0, 8)
  } catch (e) {
    /* 页面仍可输入问题 */
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
  const text = question.value.trim()
  if (!text || thinking.value) return
  messages.value.push({ role: 'user', text })
  question.value = ''
  thinking.value = true
  scrollToEnd()
  try {
    const data = await consult(text)
    lastUnmatched.value = data.matched ? '' : text
    const answerText = data.matched
      ? '【' + data.answer.category + '】' + data.answer.question + '\n' + data.answer.answer
      : '知识库中暂未找到完全匹配的答案。'
    messages.value.push({
      role: 'system',
      text: answerText,
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

function goMessages() {
  uni.navigateTo({ url: '/pages/message/message' })
}

function goLeave(text) {
  uni.setStorageSync('leaveQuestion', text || '')
  uni.navigateTo({ url: '/pages/message/message' })
}

function scrollToEnd() {
  nextTick(() => {
    lastId.value = thinking.value ? 'msg-thinking' : 'msg-' + (messages.value.length - 1)
  })
}
</script>

<style scoped>
.page {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-sizing: border-box;
}

.cats {
  white-space: nowrap;
  margin-bottom: 16rpx;
}

.cats-inner {
  display: inline-flex;
  gap: 14rpx;
}

.chip {
  display: inline-block;
  padding: 8rpx 26rpx;
  border-radius: 999rpx;
  border: 2rpx solid #dbe7dc;
  background: #ffffff;
  color: #4a5a4e;
  font-size: 24rpx;
}

.chip.active {
  background: #2e7d32;
  border-color: #2e7d32;
  color: #ffffff;
}

.hot {
  padding: 20rpx 24rpx;
  margin-bottom: 16rpx;
}

.hot-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10rpx;
}

.hot-title {
  display: block;
  font-size: 24rpx;
  font-weight: 700;
  color: #1b5e20;
}

.hot-link {
  font-size: 23rpx;
  color: #2e7d32;
}

.hot-item {
  display: block;
  font-size: 25rpx;
  color: #4a5a4e;
  padding: 8rpx 0;
  border-bottom: 2rpx solid #f4f9f4;
}

.chat {
  flex: 1;
  min-height: 300rpx;
  padding: 4rpx;
}

.chat-empty {
  padding: 30rpx 10rpx;
}

.chat-empty text {
  display: block;
  font-size: 27rpx;
  margin-bottom: 8rpx;
}

.msg {
  display: flex;
  margin-bottom: 20rpx;
}

.msg.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 78%;
  padding: 18rpx 22rpx;
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 2rpx 10rpx rgba(27, 94, 32, 0.06);
}

.msg.user .bubble {
  background: #2e7d32;
}

.bubble-text {
  font-size: 27rpx;
  white-space: pre-wrap;
}

.msg.user .bubble-text {
  color: #ffffff;
}

.rel {
  display: block;
  margin-top: 12rpx;
  color: #2e7d32;
  font-size: 24rpx;
}

.suggest {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #7c8b80;
}

.leave-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-top: 12rpx;
  padding: 12rpx 18rpx 12rpx 24rpx;
}

.leave-bar-text {
  flex: 1;
  font-size: 24rpx;
  color: #7c8b80;
}

.leave {
  display: inline-flex;
  align-items: center;
  margin: 0;
  padding: 14rpx 30rpx;
  border-radius: 999rpx;
  background: #e8f5e9;
  color: #1b5e20;
  font-size: 25rpx;
  font-weight: 600;
  line-height: 1.5;
}

.leave::after {
  border: none;
}

.leave-hover {
  background: #c8e6c9;
}

.input-bar {
  display: flex;
  align-items: center;
  padding: 14rpx 20rpx;
  margin-top: 16rpx;
}

.input-bar input {
  flex: 1;
  font-size: 28rpx;
}

.send {
  color: #2e7d32;
  font-size: 29rpx;
  font-weight: 600;
  padding-left: 20rpx;
}

.send.disabled {
  color: #b9c9bb;
}
</style>
