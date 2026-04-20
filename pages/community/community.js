const app = getApp()

Page({
  data: {
    posts: [],
    page: 1,
    hasMore: true,
    loading: false,
    searchKeyword: '',
    sortBy: 'date' // date, likes, favorites
  },

  onShow() {
    this.setData({ page: 1, posts: [] }, () => {
      this.loadPublicDreams()
    })
  },

  onPullDownRefresh() {
    this.setData({ page: 1, posts: [] }, () => {
      this.loadPublicDreams(() => {
        wx.stopPullDownRefresh()
      })
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadPublicDreams()
    }
  },

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value })
  },

  onSearch() {
    this.setData({ page: 1, posts: [] }, () => {
      this.loadPublicDreams()
    })
  },

  changeSort(e) {
    const sort = e.currentTarget.dataset.sort
    if (this.data.sortBy === sort) return
    this.setData({ sortBy: sort, page: 1, posts: [] }, () => {
      this.loadPublicDreams()
    })
  },

  loadPublicDreams(callback) {
    if (this.data.loading) return
    this.setData({ loading: true })

    const { page, searchKeyword, sortBy } = this.data
    const userId = app.globalData.currentUser ? app.globalData.currentUser.id : ''
    let url = `${app.globalData.apiBase}/community?page=${page}&limit=10&sort_by=${sortBy}&user_id=${userId}`
    if (searchKeyword) {
      url += `&keyword=${encodeURIComponent(searchKeyword)}`
    }

    app.request({
      url,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          const newPosts = res.data.map(post => ({
            ...post,
            formattedDate: new Date(post.record_date).toLocaleDateString()
          }))

          this.setData({
            posts: page === 1 ? newPosts : [...this.data.posts, ...newPosts],
            page: page + 1,
            hasMore: newPosts.length >= 10
          })
        }
      },
      complete: () => {
        this.setData({ loading: false })
        if (callback) callback()
      }
    })
  },

  goToDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  }
})
