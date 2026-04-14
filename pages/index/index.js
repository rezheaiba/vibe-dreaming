const app = getApp()

Page({
  data: {
    username: '',
    dreamInput: '',
    currentUser: null,
    dreamHistory: [],
    loading: false
  },

  onLoad() {
    if (app.globalData.currentUser) {
      this.setData({
        currentUser: app.globalData.currentUser
      })
      this.loadDreams()
    }
  },

  handleInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({
      [field]: e.detail.value
    })
  },

  login() {
    const { username } = this.data
    if (!username) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }

    wx.showLoading({ title: '登录中...' })
    wx.request({
      url: `${app.globalData.apiBase}/users`,
      method: 'POST',
      data: { username },
      success: (res) => {
        if (res.statusCode === 200) {
          const user = res.data
          app.globalData.currentUser = user
          wx.setStorageSync('currentUser', user)
          this.setData({ currentUser: user })
          this.loadDreams()
        } else {
          wx.showToast({ title: '登录失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '服务器连接失败', icon: 'none' })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },

  submitDream() {
    const { dreamInput, currentUser } = this.data
    if (!dreamInput) {
      wx.showToast({ title: '梦境内容不能为空', icon: 'none' })
      return
    }

    wx.showLoading({ title: '提交中...' })
    wx.request({
      url: `${app.globalData.apiBase}/dreams`,
      method: 'POST',
      data: {
        user_id: currentUser.id,
        content: dreamInput
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ dreamInput: '' })
          this.loadDreams()
          wx.showToast({ title: '提交成功', icon: 'success' })
        } else {
          wx.showToast({ title: '提交失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '服务器连接失败', icon: 'none' })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },

  loadDreams() {
    const { currentUser } = this.data
    if (!currentUser) return

    wx.request({
      url: `${app.globalData.apiBase}/dreams/${currentUser.id}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          // Format date if needed
          const dreams = res.data.map(d => ({
            ...d,
            formattedDate: new Date(d.record_date).toLocaleString()
          }))
          this.setData({ dreamHistory: dreams })
        }
      }
    })
  },

  logout() {
    wx.clearStorageSync()
    app.globalData.currentUser = null
    this.setData({
      currentUser: null,
      dreamHistory: [],
      username: ''
    })
  }
})
