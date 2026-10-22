<template>
  <view class="page">
    <view class="hero card">
      <text class="hero-title">拍照识病，科学防治</text>
      <text class="hero-sub">上传叶片照片，自动识别 38 类病害，并给出防治方案与防治效果判断标准</text>
      <view class="hero-stats">
        <view class="stat"><text class="stat-num">38</text><text class="stat-label">类病害</text></view>
        <view class="stat"><text class="stat-num">99.28%</text><text class="stat-label">识别准确率</text></view>
        <view class="stat"><text class="stat-num">90+</text><text class="stat-label">防治方案</text></view>
      </view>
    </view>

    <view class="upload card">
      <view v-if="!imagePath" class="choose" @click="chooseImage">
        <view class="choose-icon">+</view>
        <text class="choose-title">拍照 / 从相册选择</text>
        <text class="muted">请尽量选择病斑清晰的叶片正面照片</text>
      </view>
      <view v-else>
        <image class="preview" :src="imagePath" mode="aspectFit" />
        <view class="preview-actions">
          <text class="btn-ghost btn" @click="chooseImage">重新选择</text>
        </view>
      </view>

      <view v-if="error" class="error">{{ error }}</view>

      <button class="btn recognize" :disabled="!imagePath || loading" @click="submit">
        {{ loading ? '识别中…' : '开始识别' }}
      </button>
    </view>

    <view class="entries">
      <view class="entry card" @click="goKnowledge">
        <text class="entry-title">病害知识库</text>
        <text class="muted">38 类病害的症状、发病规律与防治方案</text>
      </view>
      <view class="entry card" @click="goConsult">
        <text class="entry-title">专家咨询</text>
        <text class="muted">常见病害问题智能问答</text>
      </view>
    </view>

    <view class="tips">
      <text class="tips-title">拍摄建议</text>
      <text class="tips-item">1. 选择病斑特征明显的部位拍摄</text>
      <text class="tips-item">2. 尽量在自然光下拍摄，避免逆光与阴影</text>
      <text class="tips-item">3. 保持画面清晰，避免模糊、过远或过近</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { uploadImage } from '../../api'

const imagePath = ref('')
const loading = ref(false)
const error = ref('')

function chooseImage() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['camera', 'album'],
    success: (res) => {
      imagePath.value = res.tempFilePaths[0]
      error.value = ''
    }
  })
}

async function submit() {
  if (!imagePath.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await uploadImage(imagePath.value)
    uni.setStorageSync('lastResult', result)
    uni.setStorageSync('lastImagePath', imagePath.value)
    uni.navigateTo({ url: '/pages/result/result' })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function goKnowledge() {
  uni.switchTab({ url: '/pages/knowledge/knowledge' })
}

function goConsult() {
  uni.switchTab({ url: '/pages/consult/consult' })
}
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.hero {
  padding: 36rpx 30rpx;
  margin-bottom: 24rpx;
}

.hero-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #1b5e20;
  margin-bottom: 12rpx;
}

.hero-sub {
  display: block;
  font-size: 26rpx;
  color: #4a5a4e;
}

.hero-stats {
  display: flex;
  margin-top: 28rpx;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 34rpx;
  font-weight: 700;
  color: #2e7d32;
}

.stat-label {
  font-size: 22rpx;
  color: #7c8b80;
}

.upload {
  padding: 28rpx;
  margin-bottom: 24rpx;
}

.choose {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 0;
  border: 3rpx dashed #dbe7dc;
  border-radius: 16rpx;
}

.choose-icon {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 56rpx;
  line-height: 84rpx;
  text-align: center;
  margin-bottom: 16rpx;
}

.choose-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 8rpx;
}

.preview {
  width: 100%;
  height: 480rpx;
  border-radius: 16rpx;
  background: #f4f9f4;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16rpx;
}

.preview-actions .btn {
  height: 68rpx;
  padding: 0 28rpx;
  font-size: 26rpx;
}

.error {
  margin-top: 20rpx;
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
  background: #fdecec;
  color: #d84343;
  font-size: 26rpx;
}

.recognize {
  margin-top: 24rpx;
}

.entries {
  display: flex;
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.entry {
  flex: 1;
  padding: 28rpx 24rpx;
}

.entry-title {
  display: block;
  font-size: 30rpx;
  font-weight: 600;
  color: #1b5e20;
  margin-bottom: 8rpx;
}

.entry .muted {
  font-size: 23rpx;
}

.tips {
  padding: 24rpx;
  border-radius: 20rpx;
  background: #fff8e1;
}

.tips-title {
  display: block;
  font-size: 26rpx;
  font-weight: 700;
  color: #a06a00;
  margin-bottom: 10rpx;
}

.tips-item {
  display: block;
  font-size: 25rpx;
  color: #6b5b20;
  margin-bottom: 6rpx;
}
</style>
