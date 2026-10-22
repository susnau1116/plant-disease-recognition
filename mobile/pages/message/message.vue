<template>
  <view class="page">
    <view class="card form">
      <text class="form-title">留言提问</text>
      <text class="muted form-sub">知识库未匹配的问题可在这里留言，工作人员回复后可在下方查看。</text>
      <textarea
        v-model="question"
        class="textarea"
        placeholder="请描述作物、症状与已采取的措施，如：番茄叶片出现褐色轮纹，已喷过一次药"
        maxlength="500"
      />
      <input
        v-model="contact"
        class="contact"
        placeholder="联系方式（选填，便于回复通知）"
        maxlength="100"
      />
      <view v-if="error" class="error">{{ error }}</view>
      <button class="btn submit" :disabled="!question.trim() || submitting" @click="submit">
        {{ submitting ? '提交中…' : '提交留言' }}
      </button>
      <text v-if="success" class="success">{{ success }}</text>
    </view>

    <view class="list-head">
      <text class="list-title">我的留言</text>
      <view class="refresh" hover-class="refresh-hover" @tap="loadMine"><text>刷新</text></view>
    </view>

    <view v-if="loading" class="loading muted">加载中…</view>
    <view v-else-if="listError" class="error">{{ listError }}</view>
    <view v-else-if="!items.length" class="card empty">
      <text class="muted">暂无留言记录，提交后可在这里查看回复。</text>
    </view>
    <view v-for="m in items" :key="m.id" class="card item">
      <view class="item-head">
        <text class="item-q">{{ m.question }}</text>
        <text :class="['tag', m.status === 'replied' ? 'tag-green' : 'tag-amber']">
          {{ m.status === 'replied' ? '已回复' : '待回复' }}
        </text>
      </view>
      <text class="muted time">{{ m.created_at }}</text>
      <view v-if="m.reply" class="reply">
        <text class="reply-label">工作人员回复</text>
        <text class="reply-text">{{ m.reply }}</text>
        <text class="muted time">{{ m.replied_at }}</text>
      </view>
      <text v-else class="muted waiting">工作人员正在处理中，请稍后刷新查看…</text>
    </view>
  </view>
</template>

<script setup>
import { onShow, onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { createMessage, getMessages } from '../../api'

const STORAGE_KEY = 'myMessageIds'

const question = ref('')
const contact = ref('')
const submitting = ref(false)
const error = ref('')
const success = ref('')
const items = ref([])
const loading = ref(false)
const listError = ref('')

onLoad((options) => {
  if (options && options.question) {
    question.value = decodeURIComponent(options.question)
    return
  }
  const pending = uni.getStorageSync('leaveQuestion')
  if (pending) {
    question.value = pending
    uni.removeStorageSync('leaveQuestion')
  }
})

onShow(() => loadMine())

function loadIds() {
  const ids = uni.getStorageSync(STORAGE_KEY)
  return Array.isArray(ids) ? ids : []
}

function saveId(id) {
  const ids = loadIds().filter((x) => x !== id)
  ids.unshift(id)
  uni.setStorageSync(STORAGE_KEY, ids.slice(0, 50))
}

async function submit() {
  const text = question.value.trim()
  if (!text || submitting.value) return
  submitting.value = true
  error.value = ''
  success.value = ''
  try {
    const data = await createMessage(text, contact.value.trim())
    saveId(data.id)
    success.value = '留言已提交，我们会尽快回复。'
    question.value = ''
    contact.value = ''
    await loadMine()
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

async function loadMine() {
  const ids = loadIds()
  if (!ids.length) {
    items.value = []
    listError.value = ''
    return
  }
  loading.value = true
  listError.value = ''
  try {
    const data = await getMessages({ ids: ids.join(',') })
    items.value = data.items
  } catch (e) {
    listError.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.form {
  padding: 26rpx;
}

.form-title {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #1b5e20;
}

.form-sub {
  display: block;
  margin: 8rpx 0 20rpx;
  font-size: 24rpx;
}

.textarea {
  width: 100%;
  min-height: 180rpx;
  padding: 18rpx;
  border: 2rpx solid #dbe7dc;
  border-radius: 14rpx;
  font-size: 27rpx;
  box-sizing: border-box;
  background: #fbfdfb;
}

.contact {
  width: 100%;
  margin-top: 16rpx;
  padding: 16rpx 18rpx;
  border: 2rpx solid #dbe7dc;
  border-radius: 14rpx;
  font-size: 26rpx;
  box-sizing: border-box;
  background: #fbfdfb;
}

.submit {
  margin-top: 22rpx;
}

.error {
  margin-top: 16rpx;
  padding: 14rpx 18rpx;
  border-radius: 12rpx;
  background: #fdecec;
  color: #d84343;
  font-size: 24rpx;
}

.success {
  display: block;
  margin-top: 16rpx;
  padding: 14rpx 18rpx;
  border-radius: 12rpx;
  background: #e8f5e9;
  color: #1b5e20;
  font-size: 24rpx;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 30rpx 4rpx 16rpx;
}

.list-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #1b5e20;
}

.refresh {
  padding: 8rpx 20rpx;
  border-radius: 999rpx;
  font-size: 25rpx;
  color: #2e7d32;
  background: #e8f5e9;
}

.refresh-hover {
  background: #c8e6c9;
}

.loading {
  padding: 24rpx 0;
  font-size: 26rpx;
}

.empty {
  padding: 30rpx;
  font-size: 26rpx;
}

.item {
  padding: 22rpx 24rpx;
  margin-bottom: 16rpx;
}

.item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.item-q {
  flex: 1;
  font-size: 28rpx;
  font-weight: 600;
}

.time {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
}

.reply {
  margin-top: 16rpx;
  padding: 16rpx 18rpx;
  border-radius: 12rpx;
  background: #f4f9f4;
}

.reply-label {
  display: block;
  font-size: 23rpx;
  font-weight: 700;
  color: #2e7d32;
}

.reply-text {
  display: block;
  margin-top: 6rpx;
  font-size: 26rpx;
  white-space: pre-wrap;
}

.waiting {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
}
</style>
