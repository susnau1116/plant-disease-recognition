import { reactive } from 'vue'

export const store = reactive({
  lastResult: null,
  lastImageUrl: '',
  setResult(result, imageUrl) {
    this.lastResult = result
    this.lastImageUrl = imageUrl
  }
})
