const app = getApp()

Page({
  data: {
    dream: null,
    isOwner: false,
    isEdit: false,
    editContent: '',
    commentTree: [],
    commentInput: '',
    currentUser: null,
    loading: true,
    replyToId: null,
    replyToRoot: null,
    replyToUser: '',
    inputFocus: false
  },

  onLoad(options) {
    this.dreamId = options.id
    this.setData({ currentUser: app.globalData.currentUser })
    this.initData()
  },

  async initData() {
    this.setData({ loading: true })
    const userId = app.globalData.currentUser ? app.globalData.currentUser.id : ''
    await Promise.all([
      this.fetchDreamDetail(userId),
      this.fetchComments(userId)
    ])
    this.setData({ loading: false })
  },

  fetchDreamDetail(userId) {
    return new Promise((resolve) => {
      app.request({
        url: `${app.globalData.apiBase}/dreams/detail/${this.dreamId}?user_id=${userId}`,
        method: 'GET',
        success: (res) => {
          if (res.statusCode === 200) {
            const dream = res.data
            dream.formattedDate = new Date(dream.record_date).toLocaleString()
            this.setData({ dream, isOwner: app.globalData.currentUser && dream.user_id === app.globalData.currentUser.id })
          }
          resolve()
        },
        fail: () => resolve()
      })
    })
  },

  fetchComments(userId) {
    return new Promise((resolve) => {
      app.request({
        url: `${app.globalData.apiBase}/comments/${this.dreamId}?user_id=${userId}`,
        method: 'GET',
        success: (res) => {
          if (res.statusCode === 200) {
            this.processCommentTree(res.data)
          }
          resolve()
        },
        fail: () => resolve()
      })
    })
  },

  // 将扁平化评论转换为树形结构（按楼层）
  processCommentTree(rawList) {
    const roots = rawList.filter(c => !c.parent_id)
    const tree = roots.map(root => {
      return {
        ...root,
        replies: rawList.filter(c => c.root_id === root.id)
      }
    })
    this.setData({ commentTree: tree })
  },

  onCommentInput(e) { this.setData({ commentInput: e.detail.value }) },

  replyComment(e) {
    const { id, root, user } = e.currentTarget.dataset
    this.setData({
      replyToId: id,
      replyToRoot: root,
      replyToUser: user,
      inputFocus: true
    })
  },

  submitComment() {
    if (!this.data.commentInput) return
    if (!app.globalData.currentUser) { wx.showToast({ title: '登录后可评论', icon: 'none' }); return }

    app.request({
      url: `${app.globalData.apiBase}/comments`,
      method: 'POST',
      data: {
        dream_id: this.dreamId,
        user_id: app.globalData.currentUser.id,
        content: this.data.commentInput,
        parent_id: this.data.replyToId,
        root_id: this.data.replyToRoot
      },
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已发送' })
          this.setData({ commentInput: '', replyToId: null, replyToRoot: null, replyToUser: '' })
          this.fetchComments(app.globalData.currentUser.id)
          this.fetchDreamDetail(app.globalData.currentUser.id)
        }
      }
    })
  },

  deleteComment(e) {
    const { id } = e.currentTarget.dataset
    wx.showModal({
      title: '确认删除',
      content: '删除操作无法撤回',
      success: (res) => {
        if (res.confirm) {
          app.request({
            url: `${app.globalData.apiBase}/comments/${id}?user_id=${app.globalData.currentUser.id}`,
            method: 'DELETE',
            success: () => {
              wx.showToast({ title: '已删除' })
              this.fetchComments(app.globalData.currentUser.id)
              this.fetchDreamDetail(app.globalData.currentUser.id)
            }
          })
        }
      }
    })
  },

  likeComment(e) {
    if (!app.globalData.currentUser) { wx.showToast({ title: '登录后可点赞', icon: 'none' }); return }
    const { id } = e.currentTarget.dataset
    app.request({
      url: `${app.globalData.apiBase}/comments/like/${id}?user_id=${app.globalData.currentUser.id}`,
      method: 'POST',
      success: () => {
        this.fetchComments(app.globalData.currentUser.id)
      }
    })
  },

  // 基础操作逻辑保留
  startEdit() { this.setData({ isEdit: true, editContent: this.data.dream.raw_content }) },
  cancelEdit() { this.setData({ isEdit: false }) },
  onEditInput(e) { this.setData({ editContent: e.detail.value }) },
  saveEdit() {
    if (!this.data.editContent) return
    app.request({
      url: `${app.globalData.apiBase}/dreams/${this.dreamId}`,
      method: 'PUT',
      data: { user_id: app.globalData.currentUser.id, content: this.data.editContent },
      success: () => {
        wx.showToast({ title: '更新成功' })
        this.setData({ isEdit: false })
        this.fetchDreamDetail(app.globalData.currentUser.id)
        app.globalData.needsReload = true
      }
    })
  },
  toggleLike() {
    if (!app.globalData.currentUser) { wx.showToast({ title: '登录后可点赞', icon: 'none' }); return }
    app.request({
      url: `${app.globalData.apiBase}/dreams/like/${this.dreamId}?user_id=${app.globalData.currentUser.id}`,
      method: 'POST',
      success: () => { this.fetchDreamDetail(app.globalData.currentUser.id) }
    })
  },
  toggleFav() {
    if (!app.globalData.currentUser) { wx.showToast({ title: '登录后可收藏', icon: 'none' }); return }
    app.request({
      url: `${app.globalData.apiBase}/dreams/fav/${this.dreamId}?user_id=${app.globalData.currentUser.id}`,
      method: 'POST',
      success: () => { this.fetchDreamDetail(app.globalData.currentUser.id) }
    })
  },
  deleteDream() {
    wx.showModal({
      title: '删除梦境',
      content: '确定要永远告别这个梦吗？',
      confirmColor: '#ff4757',
      success: (sm) => {
        if (sm.confirm) {
          app.request({
            url: `${app.globalData.apiBase}/dreams/${this.dreamId}?user_id=${app.globalData.currentUser.id}`,
            method: 'DELETE',
            success: () => {
              wx.showToast({ title: '已删除' })
              app.globalData.needsReload = true
              setTimeout(() => wx.navigateBack(), 1000)
            }
          })
        }
      }
    })
  }
})
