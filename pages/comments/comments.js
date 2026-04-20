const app = getApp()

Page({
  data: {
    dreamId: null,
    dream: null,
    comments: [],
    newComment: '',
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ dreamId: options.id })
      this.loadDreamAndComments()
    }
  },

  loadDreamAndComments() {
    const { dreamId } = this.data
    
    // 加载梦境信息
    wx.request({
      url: `${app.globalData.apiBase}/dreams/detail/${dreamId}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ dream: res.data })
        }
      }
    })

    // 加载评论
    this.loadComments()
  },

  loadComments() {
    const { dreamId } = this.data
    
    wx.request({
      url: `${app.globalData.apiBase}/comments/${dreamId}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          const comments = res.data.map(c => ({
            ...c,
            formattedDate: new Date(c.created_at).toLocaleString()
          }))
          this.setData({ comments })
        }
      }
    })
  },

  handleInput(e) {
    this.setData({ newComment: e.detail.value })
  },

  submitComment() {
    const currentUser = app.globalData.currentUser
    const { dreamId, newComment } = this.data
    
    if (!currentUser) {
      wx.showToast({ title: '请先登录', icon: 'none' })
      return
    }
    
    if (!newComment.trim()) {
      wx.showToast({ title: '请输入评论内容', icon: 'none' })
      return
    }

    wx.showLoading({ title: '发送中...' })
    wx.request({
      url: `${app.globalData.apiBase}/comments`,
      method: 'POST',
      data: {
        dream_id: dreamId,
        user_id: currentUser.id,
        content: newComment.trim()
      },
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '评论成功', icon: 'success' })
          this.setData({ newComment: '' })
          this.loadComments()
        } else {
          wx.showToast({ title: '发送失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '网络错误', icon: 'none' })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },

  deleteComment(e) {
    const { id } = e.currentTarget.dataset
    const currentUser = app.globalData.currentUser
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条评论吗？',
      success: (res) => {
        if (res.confirm) {
          wx.request({
            url: `${app.globalData.apiBase}/comments/${id}`,
            method: 'DELETE',
            data: { user_id: currentUser.id },
            success: (res) => {
              if (res.statusCode === 200) {
                wx.showToast({ title: '删除成功', icon: 'success' })
                this.loadComments()
              }
            }
          })
        }
      }
    })
  }
})
