<template>
  <view class="page">
    <template v-if="result">
      <view class="head card">
        <image v-if="imagePath" class="head-image" :src="imagePath" mode="aspectFit" />
        <view class="head-info">
          <view class="tags">
            <text class="tag tag-blue">{{ result.crop }}</text>
            <text :class="['tag', result.healthy ? 'tag-green' : 'tag-red']">
              {{ result.healthy ? '健康' : '病害' }}
            </text>
          </view>
          <text class="name">{{ result.name_cn }}</text>
          <text class="muted">{{ result.disease.name_en }}</text>
          <view class="conf">
            <view class="conf-track">
              <view class="conf-fill" :style="{ width: (result.confidence * 100).toFixed(1) + '%' }"></view>
            </view>
            <text class="conf-text">置信度 {{ (result.confidence * 100).toFixed(2) }}%</text>
          </view>
          <text class="muted">推理耗时 {{ result.inference_ms }} ms</text>
        </view>
      </view>

      <view class="card block">
        <text class="block-title">其他可能</text>
        <view v-for="item in otherTopK" :key="item.class_name" class="topk-item">
          <view class="topk-line">
            <text>{{ item.name_cn }}</text>
            <text class="muted">{{ (item.confidence * 100).toFixed(2) }}%</text>
          </view>
          <view class="conf-track small">
            <view class="conf-fill" :style="{ width: (item.confidence * 100).toFixed(1) + '%' }"></view>
          </view>
        </view>
      </view>

      <view class="card block">
        <text class="block-title">{{ result.healthy ? '状态说明' : '病害信息' }}</text>
        <view class="info-item"><text class="info-key">症状表现</text><text class="info-val">{{ result.disease.symptoms || '—' }}</text></view>
        <view class="info-item"><text class="info-key">发病规律</text><text class="info-val">{{ result.disease.occurrence || '—' }}</text></view>
        <view class="info-item"><text class="info-key">传播途径</text><text class="info-val">{{ result.disease.transmission || '—' }}</text></view>
      </view>

      <view v-if="examples.length" class="card block">
        <text class="block-title">{{ result.healthy ? '健康叶片参考例图' : '病害参考例图' }}</text>
        <view class="shots">
          <image
            v-for="(img, i) in examples"
            :key="img"
            class="shot"
            :src="img"
            mode="aspectFill"
            @click="previewExamples(i)"
          />
        </view>
        <text class="hint">点击图片放大，与上传图片对照</text>
      </view>

      <view class="block-title out-title">{{ result.healthy ? '栽培与预防建议' : '防治方案' }}</view>
      <treatment-card v-for="(t, i) in result.disease.treatments" :key="i" :treatment="t" />

      <view class="actions">
        <button class="btn-ghost btn" @click="goHome">再识别一张</button>
        <button class="btn" @click="goConsult">咨询专家</button>
      </view>
    </template>

    <view v-else class="empty card">
      <text class="empty-title">暂无识别结果</text>
      <text class="muted">请先在识别页上传叶片图片</text>
      <button class="btn empty-btn" @click="goHome">去识别</button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TreatmentCard from '../../components/treatment-card.vue'

const result = ref(null)
const imagePath = ref('')

onShow(() => {
  result.value = uni.getStorageSync('lastResult') || null
  imagePath.value = uni.getStorageSync('lastImagePath') || ''
})

const otherTopK = computed(() => (result.value && result.value.top_k ? result.value.top_k.slice(1) : []))
const examples = computed(() =>
  result.value && result.value.disease && result.value.disease.examples
    ? result.value.disease.examples
    : []
)

function previewExamples(index) {
  uni.previewImage({ urls: examples.value, current: index })
}

function goHome() {
  uni.switchTab({ url: '/pages/index/index' })
}

function goConsult() {
  uni.switchTab({ url: '/pages/consult/consult' })
}
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.head {
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.head-image {
  width: 100%;
  height: 420rpx;
  border-radius: 16rpx;
  background: #f4f9f4;
  margin-bottom: 20rpx;
}

.tags {
  display: flex;
  gap: 12rpx;
  margin-bottom: 12rpx;
}

.name {
  display: block;
  font-size: 38rpx;
  font-weight: 700;
  color: #1b5e20;
}

.conf {
  margin: 20rpx 0 8rpx;
}

.conf-track {
  height: 14rpx;
  border-radius: 999rpx;
  background: #e8f5e9;
  overflow: hidden;
}

.conf-track.small {
  height: 10rpx;
}

.conf-fill {
  height: 100%;
  border-radius: 999rpx;
  background: #43a047;
}

.conf-text {
  display: block;
  font-size: 24rpx;
  color: #4a5a4e;
  margin-top: 8rpx;
}

.block {
  padding: 26rpx;
  margin-bottom: 20rpx;
}

.block-title {
  display: block;
  font-size: 30rpx;
  font-weight: 700;
  color: #1b5e20;
  margin-bottom: 16rpx;
}

.shots {
  display: flex;
  gap: 12rpx;
}

.shot {
  flex: 1;
  height: 190rpx;
  border-radius: 12rpx;
  background: #f4f9f4;
}

.hint {
  display: block;
  font-size: 22rpx;
  color: #7c8b80;
  margin-top: 12rpx;
}

.topk-item {
  margin-bottom: 14rpx;
}

.topk-line {
  display: flex;
  justify-content: space-between;
  font-size: 25rpx;
  margin-bottom: 6rpx;
}

.info-item {
  margin-bottom: 14rpx;
}

.info-key {
  display: block;
  font-size: 24rpx;
  color: #2e7d32;
  font-weight: 600;
}

.info-val {
  font-size: 26rpx;
  color: #4a5a4e;
}

.out-title {
  margin: 10rpx 4rpx 16rpx;
}

.actions {
  display: flex;
  gap: 20rpx;
  margin: 30rpx 0 10rpx;
}

.actions .btn {
  flex: 1;
}

.empty {
  padding: 100rpx 40rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 600;
  margin-bottom: 10rpx;
}

.empty-btn {
  margin-top: 30rpx;
  width: 320rpx;
}
</style>
