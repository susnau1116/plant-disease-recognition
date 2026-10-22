<script>
export default {
  onLaunch() {
    console.log('农作物病害识别与防治系统启动')
  }
}
</script>

<style>
page {
  background-color: #f4f9f4;
  color: #1f2d22;
  font-size: 28rpx;
  line-height: 1.6;
}

.card {
  background: #ffffff;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 16rpx rgba(27, 94, 32, 0.06);
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 88rpx;
  border-radius: 16rpx;
  background: #2e7d32;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}

.btn[disabled] {
  background: #b9c9bb;
  color: #eef4ee;
}

.btn-ghost {
  background: #ffffff;
  color: #2e7d32;
  border: 2rpx solid #2e7d32;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2rpx 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.tag-green {
  background: #e8f5e9;
  color: #1b5e20;
}

.tag-red {
  background: #fdecec;
  color: #d84343;
}

.tag-blue {
  background: #e8f1fa;
  color: #2f6fb2;
}

.tag-amber {
  background: #fff8e1;
  color: #a06a00;
}

.muted {
  color: #7c8b80;
}

.mt {
  margin-top: 20rpx;
}
</style>
