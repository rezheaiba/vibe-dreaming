App({
  globalData: {
    currentUser: null,
    apiBase: 'http://127.0.0.1:8000'
  },
  onLaunch() {
    // Check if user info is in storage
    const user = wx.getStorageSync('currentUser');
    if (user) {
      this.globalData.currentUser = user;
    }
  }
})
