<template>
  <view class="page">
    <view v-if="loading" class="loading">加载中…</view>
    <view v-else-if="error" class="error">{{ error }}</view>
    <template v-else-if="disease">
      <view class="head card">
        <view class="tags">
          <text class="tag tag-blue">{{ disease.crop }}</text>
          <text :class="['tag', disease.healthy ? 'tag-green' : 'tag-red']">
            {{ disease.healthy ? '健康' : '病害' }}
          </text>
        </view>
        <text class="name">{{ disease.name_cn }}</text>
        <text class="muted">{{ disease.name_en }}</text>
      </view>

      <view v-if="disease.examples && disease.examples.length" class="card block">
        <text class="block-title">{{ disease.healthy ? '健康叶片例图' : '病害例图' }}</text>
        <view class="shots">
          <image
            v-for="(img, i) in disease.examples"
            :key="img"
            class="shot"
            :src="img"
            mode="aspectFill"
            @click="previewExamples(i)"
          />
        </view>
        <text class="hint">点击图片放大对照（PlantVillage 典型样本）</text>
      </view>

      <view class="card block">
        <text class="block-title">{{ disease.healthy ? '状态说明' : '病害信息' }}</text>
        <view class="info-item"><text class="info-key">症状表现</text><text class="info-val">{{ disease.symptoms || '—' }}</text></view>
        <view class="info-item"><text class="info-key">发病规律</text><text class="info-val">{{ disease.occurrence || '—' }}</text></view>
        <view class="info-item"><text class="info-key">传播途径</text><text class="info-val">{{ disease.transmission || '—' }}</text></view>
      </view>

      <view class="block-title out-title">{{ disease.healthy ? '栽培与预防建议' : '防治方案' }}</view>
      <treatment-card v-for="(t, i) in disease.treatments" :key="i" :treatment="t" />

      <view class="ask">
        <button class="btn" @click="goConsult">有疑问？咨询专家</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import TreatmentCard from '../../components/treatment-card.vue'
import { getDisease } from '../../api'

const disease = ref(null)
const loading = ref(true)
const error = ref('')

onLoad(async (options) => {
  const className = decodeURIComponent(options.className || '')
  if (!className) {
    error.value = '缺少病害类别参数'
    loading.value = false
    return
  }
  try {
    disease.value = await getDisease(className)
    uni.setNavigationBarTitle({ title: disease.value.name_cn })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

function goConsult() {
  uni.switchTab({ url: '/pages/consult/consult' })
}

function previewExamples(index) {
  if (!disease.value) return
  uni.previewImage({ urls: disease.value.examples, current: index })
}
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.loading,
.error {
  padding: 60rpx 0;
  text-align: center;
  color: #7c8b80;
}

.error {
  color: #d84343;
}

.head {
  padding: 28rpx;
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
  margin-bottom: 4rpx;
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

.ask {
  margin: 30rpx 0 10rpx;
}
</style>
