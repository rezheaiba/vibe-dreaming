App({
  globalData: {
    currentUser: null,
    apiBase: 'http://127.0.0.1:8000',
    needsReload: false // 全局刷新信号
  },
  onLaunch() {
    const user = wx.getStorageSync('currentUser');
    if (user) {
      this.globalData.currentUser = user;
    }
  },

  checkLogin() {
    if (!this.globalData.currentUser) {
      wx.showModal({
        title: '请先登录',
        content: '登录后即可体验完整功能',
        confirmText: '去首页',
        showCancel: false,
        success: () => {
          wx.switchTab({ url: '/pages/index/index' });
        }
      });
      return false;
    }
    return true;
  },

  request(options) {
    const originalSuccess = options.success;
    options.success = (res) => {
      if (res.statusCode === 403) {
        wx.showToast({ title: '权限失效', icon: 'none' });
        this.logout();
      }
      if (originalSuccess) originalSuccess(res);
    };
    wx.request(options);
  },

  logout() {
    this.globalData.currentUser = null;
    wx.removeStorageSync('currentUser');
    wx.showLoading({ title: '退出中...' });
    setTimeout(() => {
      wx.hideLoading();
      wx.reLaunch({ url: '/pages/index/index' });
    }, 300);
  }
})
