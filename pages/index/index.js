const app = getApp()

Page({
  data: {
    username: '',
    currentUser: null,
    dreamInput: '',
    searchKeyword: '',
    dreams: [],
    filteredDreams: [],
    isLoginLoading: true, // 新增：标记是否正在尝试自动登录
    autoAi: true
  },

  onLoad() {
    const status = app.globalData.autoLoginStatus
    if (app.globalData.currentUser) {
      this.setData({ currentUser: app.globalData.currentUser, isLoginLoading: false })
      this.loadDreams()
    } else if (status === 'failed') {
      this.setData({ isLoginLoading: false })
    } else {
      this.setData({ isLoginLoading: true })
      // 尝试自动登录
      app.userInfoReadyCallback = user => {
        this.setData({ currentUser: user, isLoginLoading: false })
        this.loadDreams()
      }
      // 如果自动登录失败（如网络问题或后端未配置），则显示手动登录
      app.loginFailedCallback = () => {
        this.setData({ isLoginLoading: false })
        wx.showToast({ title: '自动登录失败，请手动尝试', icon: 'none' })
      }
    }
  },

  onShow() {
    // 强制同步登录态与刷新信号
    const user = app.globalData.currentUser;
    const shouldReload = app.globalData.needsReload;

    if (user) {
      if (!this.data.currentUser || user.id !== this.data.currentUser.id || shouldReload) {
        this.setData({ currentUser: user })
        app.globalData.needsReload = false // 重置信号
        this.loadDreams()
      }
    } else {
      this.setData({ currentUser: null, dreams: [], filteredDreams: [] })
    }
  },

  handleInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  login() {
    if (!this.data.username) {
      wx.showToast({ title: '请输入昵称', icon: 'none' }); return
    }
    app.request({
      url: `${app.globalData.apiBase}/users`,
      method: 'POST',
      data: { username: this.data.username },
      success: (res) => {
        if (res.statusCode === 200) {
          const user = res.data
          app.globalData.currentUser = user
          app.globalData.autoLoginStatus = 'success'
          wx.setStorageSync('currentUser', user)
          this.setData({ currentUser: user })
          this.loadDreams()
        }
      }
    })
  },

  toggleAutoAi(e) {
    this.setData({ autoAi: e.detail.value })
  },

  submitDream() {
    if (!this.data.dreamInput) {
      wx.showToast({ title: '请输入梦境内容', icon: 'none' }); return
    }
    const loadingTitle = this.data.autoAi ? 'AI处理中...' : '正在记梦...'
    wx.showLoading({ title: loadingTitle })
    app.request({
      url: `${app.globalData.apiBase}/dreams`,
      method: 'POST',
      data: { 
        user_id: this.data.currentUser.id, 
        content: this.data.dreamInput, 
        is_public: 0,
        auto_ai: this.data.autoAi
      },
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已入梦', icon: 'success' })
          this.setData({ dreamInput: '' })
          this.loadDreams()
        } else {
          wx.showToast({ title: '保存失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '网络异常', icon: 'none' })
      },
      complete: () => wx.hideLoading()
    })
  },

  loadDreams() {
    if (!this.data.currentUser) return
    app.request({
      url: `${app.globalData.apiBase}/dreams/user/${this.data.currentUser.id}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          const dreams = res.data.map(d => ({
            ...d,
            formattedDate: new Date(d.record_date).toLocaleDateString(),
            shortContent: d.raw_content.length > 80 ? d.raw_content.substring(0, 80) + '...' : d.raw_content
          }))
          this.setData({ dreams, filteredDreams: dreams })
        }
      }
    })
  },

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value })
    if (!e.detail.value) this.setData({ filteredDreams: this.data.dreams })
  },

  onSearch() {
    const keyword = this.data.searchKeyword.toLowerCase()
    if (!keyword) {
      this.setData({ filteredDreams: this.data.dreams }); return
    }
    const filtered = this.data.dreams.filter(d => d.raw_content.toLowerCase().includes(keyword))
    this.setData({ filteredDreams: filtered })
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
  }
})
