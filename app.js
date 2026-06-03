App({
  globalData: {
    currentUser: null,
    apiBase: 'http://127.0.0.1:8000',
    needsReload: false, // 全局刷新信号
    autoLoginStatus: 'pending' // pending, success, failed
  },
  onLaunch() {
    const user = wx.getStorageSync('currentUser');
    if (user) {
      this.globalData.currentUser = user;
      this.globalData.autoLoginStatus = 'success';
    } else {
      this.globalData.autoLoginStatus = 'pending';
      this.autoWeChatLogin();
    }
  },

  autoWeChatLogin() {
    wx.login({
      success: (res) => {
        if (res.code) {
          wx.request({
            url: `${this.globalData.apiBase}/wechat_login`,
            method: 'POST',
            data: { code: res.code },
            success: (loginRes) => {
              if (loginRes.statusCode === 200) {
                const user = loginRes.data;
                this.globalData.currentUser = user;
                this.globalData.autoLoginStatus = 'success';
                wx.setStorageSync('currentUser', user);
                if (this.userInfoReadyCallback) {
                  this.userInfoReadyCallback(user);
                }
              } else {
                console.error('WeChat Login Failed:', loginRes.data);
                this.globalData.autoLoginStatus = 'failed';
                if (this.loginFailedCallback) this.loginFailedCallback();
              }
            },
            fail: (err) => {
              console.error('Network Error:', err);
              this.globalData.autoLoginStatus = 'failed';
              if (this.loginFailedCallback) this.loginFailedCallback();
            }
          });
        }
      },
      fail: () => {
        this.globalData.autoLoginStatus = 'failed';
        if (this.loginFailedCallback) this.loginFailedCallback();
      }
    });
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
    this.globalData.autoLoginStatus = 'failed';
    wx.removeStorageSync('currentUser');
    wx.showLoading({ title: '退出中...' });
    setTimeout(() => {
      wx.hideLoading();
      wx.reLaunch({ url: '/pages/index/index' });
    }, 300);
  }
})
