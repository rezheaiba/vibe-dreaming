const app = getApp()

Page({
  data: {
    currentUser: null,
    activeTab: 'mine', 
    displayList: [],
    loading: false
  },

  onShow() {
    if (app.checkLogin()) {
      this.setData({ currentUser: app.globalData.currentUser })
      this.loadListData()
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab }, () => this.loadListData())
  },

  loadListData() {
    const { activeTab, currentUser } = this.data
    this.setData({ loading: true, displayList: [] })
    
    let url = ''
    if (activeTab === 'mine') url = `${app.globalData.apiBase}/dreams/user/${currentUser.id}`
    else if (activeTab === 'favs') url = `${app.globalData.apiBase}/dreams/faved/${currentUser.id}`
    else if (activeTab === 'likes') url = `${app.globalData.apiBase}/dreams/liked/${currentUser.id}`
    else if (activeTab === 'admin') url = `${app.globalData.apiBase}/admin/dreams?admin_id=${currentUser.id}`

    app.request({
      url,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          const list = res.data.map(d => ({
            ...d,
            formattedDate: new Date(d.record_date).toLocaleDateString()
          }))
          this.setData({ displayList: list })
        }
      },
      complete: () => this.setData({ loading: false })
    })
  },

  onTogglePublic(e) {
    const { id, current } = e.currentTarget.dataset
    const newState = current === 1 ? 0 : 1
    
    app.request({
      url: `${app.globalData.apiBase}/dreams/${id}`,
      method: 'PUT',
      data: { user_id: this.data.currentUser.id, is_public: newState },
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已更新', icon: 'none' })
          this.loadListData()
          app.globalData.needsReload = true // 触发首页刷新
        }
      }
    })
  },

  onDeleteDream(e) {
    const { id } = e.currentTarget.dataset
    const isAdmin = this.data.activeTab === 'admin'
    
    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复，确定吗？',
      success: (sm) => {
        if (sm.confirm) {
          const url = isAdmin 
            ? `${app.globalData.apiBase}/admin/dream/${id}?admin_id=${this.data.currentUser.id}`
            : `${app.globalData.apiBase}/dreams/${id}?user_id=${this.data.currentUser.id}`
          
          app.request({
            url,
            method: 'DELETE',
            success: () => {
              wx.showToast({ title: '已删除' })
              this.loadListData()
              app.globalData.needsReload = true // 关键：标记首页需要重新加载
            }
          })
        }
      }
    })
  },

  editSignature() {
    wx.showModal({
      title: '设置签名',
      editable: true,
      placeholder: '写下你的织梦格言...',
      content: this.data.currentUser.signature,
      success: (res) => {
        if (res.confirm) {
          app.request({
            url: `${app.globalData.apiBase}/users/${this.data.currentUser.id}`,
            method: 'PUT',
            data: { signature: res.content },
            success: () => {
              const user = { ...this.data.currentUser, signature: res.content }
              app.globalData.currentUser = user
              wx.setStorageSync('currentUser', user)
              this.setData({ currentUser: user })
              wx.showToast({ title: '修改成功' })
            }
          })
        }
      }
    })
  },

  logout() { app.logout() },

  goToDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
  },

  stopBubble() {}
})
