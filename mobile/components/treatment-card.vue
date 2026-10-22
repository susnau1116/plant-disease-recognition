<template>
  <view class="treatment card">
    <view class="head">
      <text :class="['tag', typeTag]">{{ treatment.type }}</text>
      <text class="name">{{ treatment.name }}</text>
    </view>
    <view v-if="show('formulation')" class="row"><text class="key">剂型</text><text class="val">{{ treatment.formulation }}</text></view>
    <view v-if="show('dosage')" class="row"><text class="key">用量</text><text class="val">{{ treatment.dosage }}</text></view>
    <view v-if="show('usage')" class="row"><text class="key">用法</text><text class="val">{{ treatment.usage }}</text></view>
    <view v-if="show('precautions')" class="row"><text class="key">注意</text><text class="val">{{ treatment.precautions }}</text></view>
    <view class="effect">
      <text class="effect-title">防治效果</text>
      <view class="effect-item"><text class="effect-key">预期效果</text><text class="effect-val">{{ treatment.expected_effect || '—' }}</text></view>
      <view class="effect-item"><text class="effect-key">见效时间</text><text class="effect-val">{{ treatment.effect_time || '—' }}</text></view>
      <view class="effect-item"><text class="effect-key">判断标准</text><text class="effect-val">{{ treatment.judgement || '—' }}</text></view>
      <view class="effect-item"><text class="effect-key">未达预期</text><text class="effect-val">{{ treatment.fallback || '—' }}</text></view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  treatment: { type: Object, required: true }
})

const typeTag = computed(() => {
  const t = props.treatment.type || ''
  if (t.indexOf('农药') >= 0) return 'tag-green'
  if (t.indexOf('物理') >= 0) return 'tag-blue'
  return 'tag-amber'
})

function show(key) {
  const v = props.treatment[key]
  return v && v !== '—'
}
</script>

<style scoped>
.treatment {
  padding: 28rpx;
  margin-bottom: 20rpx;
}

.head {
  display: flex;
  align-items: center;
  margin-bottom: 16rpx;
}

.name {
  margin-left: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
}

.row {
  display: flex;
  margin-bottom: 10rpx;
  font-size: 26rpx;
}

.key {
  flex: 0 0 88rpx;
  color: #7c8b80;
}

.val {
  flex: 1;
  color: #4a5a4e;
}

.effect {
  margin-top: 16rpx;
  background: #f4f9f4;
  border: 2rpx solid #e8f5e9;
  border-radius: 14rpx;
  padding: 18rpx 20rpx;
}

.effect-title {
  display: block;
  font-size: 24rpx;
  font-weight: 700;
  color: #1b5e20;
  margin-bottom: 10rpx;
}

.effect-item {
  margin-bottom: 8rpx;
}

.effect-key {
  display: block;
  font-size: 22rpx;
  color: #2e7d32;
}

.effect-val {
  font-size: 25rpx;
  color: #4a5a4e;
}
</style>
