<template>
  <view class="page">
    <view class="search card">
      <input v-model="keyword" placeholder="搜索病害名称或症状，如：晚疫病" confirm-type="search" @confirm="search" />
      <text class="search-btn" @click="search">搜索</text>
    </view>

    <view class="crops-wrap">
      <scroll-view class="crops" scroll-x @scroll="onCropsScroll">
        <view class="crops-inner">
          <text :class="['chip', { active: !crop }]" @click="selectCrop('')">全部</text>
          <text
            v-for="c in crops"
            :key="c.crop"
            :class="['chip', { active: crop === c.crop }]"
            @click="selectCrop(c.crop)"
          >
            {{ c.crop }} ({{ c.total }})
          </text>
        </view>
      </scroll-view>
      <view v-if="cropsCanScroll && cropsScrollLeft > 10" class="crops-fade crops-fade-left">
        <text class="crops-arrow">‹</text>
      </view>
      <view v-if="cropsCanScroll && !cropsAtEnd" class="crops-fade crops-fade-right">
        <text class="crops-arrow">›</text>
      </view>
    </view>

    <view v-if="loading" class="loading">加载中…</view>
    <view v-else-if="error" class="error">{{ error }}</view>
    <template v-else>
      <text class="count muted">共 {{ total }} 条结果</text>
      <view v-for="d in items" :key="d.class_name" class="dcard card" @click="openDetail(d.class_name)">
        <view class="dcard-head">
          <text class="dcard-name">{{ d.name_cn }}</text>
          <text :class="['tag', d.healthy ? 'tag-green' : 'tag-red']">{{ d.healthy ? '健康' : '病害' }}</text>
        </view>
        <view class="dcard-meta">
          <text class="tag tag-blue">{{ d.crop }}</text>
          <text class="muted dcard-en">{{ d.name_en }}</text>
        </view>
        <text class="dcard-symptom">{{ d.symptoms }}</text>
      </view>

      <view v-if="total > items.length" class="load-more">
        <text class="btn-ghost btn" @click="loadMore">加载更多</text>
      </view>
    </template>
  </view>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { getCrops, getDiseases } from '../../api'

const crops = ref([])
const keyword = ref('')
const crop = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const error = ref('')
const cropsScrollLeft = ref(0)
const cropsCanScroll = ref(false)
const cropsAtEnd = ref(false)
let cropsMaxScroll = 0

onMounted(async () => {
  try {
    crops.value = await getCrops()
  } catch (e) {
    crops.value = []
  }
  fetchList(true)
  nextTick(() => setTimeout(measureCrops, 300))
})

function measureCrops() {
  uni
    .createSelectorQuery()
    .select('.crops')
    .boundingClientRect()
    .select('.crops-inner')
    .boundingClientRect()
    .exec((res) => {
      if (!res || !res[0] || !res[1]) return
      cropsMaxScroll = Math.max(0, res[1].width - res[0].width)
      cropsCanScroll.value = cropsMaxScroll > 20
      cropsAtEnd.value = cropsScrollLeft.value >= cropsMaxScroll - 10
    })
}

function onCropsScroll(e) {
  cropsScrollLeft.value = e.detail.scrollLeft
  cropsAtEnd.value = cropsMaxScroll > 0 && cropsScrollLeft.value >= cropsMaxScroll - 10
}

async function fetchList(reset) {
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
    items.value = reset ? data.items : items.value.concat(data.items)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  fetchList(true)
}

function selectCrop(value) {
  crop.value = value
  page.value = 1
  fetchList(true)
}

function loadMore() {
  page.value += 1
  fetchList(false)
}

function openDetail(className) {
  uni.navigateTo({ url: '/pages/knowledge/detail?className=' + encodeURIComponent(className) })
}
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.search {
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  margin-bottom: 20rpx;
}

.search input {
  flex: 1;
  font-size: 28rpx;
}

.search-btn {
  color: #2e7d32;
  font-size: 28rpx;
  font-weight: 600;
  padding-left: 20rpx;
}

.crops-wrap {
  position: relative;
  margin-bottom: 20rpx;
}

.crops {
  white-space: nowrap;
}

.crops-inner {
  display: inline-flex;
  gap: 14rpx;
  padding-right: 24rpx;
}

.crops-fade {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 76rpx;
  pointer-events: none;
}

.crops-fade-left {
  left: 0;
  background: linear-gradient(to left, rgba(244, 249, 244, 0), #f4f9f4 62%);
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.crops-fade-left .crops-arrow {
  padding-right: 0;
  padding-left: 6rpx;
}

.crops-fade-right {
  right: 0;
  background: linear-gradient(to right, rgba(244, 249, 244, 0), #f4f9f4 62%);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.crops-arrow {
  color: #2e7d32;
  font-size: 46rpx;
  font-weight: 600;
  line-height: 1;
  padding-right: 6rpx;
}

.chip {
  display: inline-block;
  flex: none;
  white-space: nowrap;
  padding: 8rpx 26rpx;
  border-radius: 999rpx;
  border: 2rpx solid #dbe7dc;
  background: #ffffff;
  color: #4a5a4e;
  font-size: 25rpx;
}

.chip.active {
  background: #2e7d32;
  border-color: #2e7d32;
  color: #ffffff;
}

.count {
  display: block;
  font-size: 24rpx;
  margin-bottom: 16rpx;
}

.loading,
.error {
  padding: 40rpx 0;
  text-align: center;
  color: #7c8b80;
}

.error {
  color: #d84343;
}

.dcard {
  padding: 26rpx;
  margin-bottom: 20rpx;
}

.dcard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dcard-name {
  font-size: 30rpx;
  font-weight: 600;
}

.dcard-meta {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin: 12rpx 0;
}

.dcard-en {
  font-size: 22rpx;
}

.dcard-symptom {
  display: block;
  font-size: 25rpx;
  color: #4a5a4e;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.load-more {
  display: flex;
  justify-content: center;
  margin: 10rpx 0 30rpx;
}

.load-more .btn {
  width: 300rpx;
  height: 72rpx;
  font-size: 27rpx;
}
</style>
