const app = getApp()

Page({
  data: {
    streak: 0,
    totalCheckins: 0,
    isChecked: false,
    isTodayChecked: false,
    currentYear: 0,
    currentMonth: 0,
    calendarDays: [],
    checkinDates: [] // YYYY-MM-DD
  },

  onLoad() {
    const now = new Date()
    this.setData({
      currentYear: now.getFullYear(),
      currentMonth: now.getMonth()
    })
  },

  onShow() {
    // 强制登录拦截
    if (app.checkLogin()) {
      this.loadCheckins()
    }
  },

  loadCheckins() {
    app.request({
      url: `${app.globalData.apiBase}/checkin/${app.globalData.currentUser.id}`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          const checkinDates = res.data
          this.setData({ checkinDates })
          this.calculateStats(checkinDates)
          this.generateCalendar()
        }
      }
    })
  },

  calculateStats(dates) {
    if (dates.length === 0) {
      this.setData({ streak: 0, totalCheckins: 0, isTodayChecked: false })
      return
    }

    const todayStr = this.getTodayStr()
    const isTodayChecked = dates.includes(todayStr)
    
    let currentStreak = 0
    let tempDate = isTodayChecked ? new Date() : new Date(new Date().setDate(new Date().getDate() - 1))
    
    while (dates.includes(this.formatDate(tempDate))) {
      currentStreak++
      tempDate.setDate(tempDate.getDate() - 1)
    }

    this.setData({
      totalCheckins: dates.length,
      streak: currentStreak,
      isTodayChecked
    })
  },

  getTodayStr() { return this.formatDate(new Date()) },

  formatDate(date) {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  },

  generateCalendar() {
    const { currentYear, currentMonth, checkinDates } = this.data
    const firstDay = new Date(currentYear, currentMonth, 1).getDay()
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate()
    
    const days = []
    for (let i = 0; i < firstDay; i++) days.push({ isOtherMonth: true })
    for (let i = 1; i <= daysInMonth; i++) {
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`
      days.push({
        date: i,
        fullDate: dateStr,
        checked: checkinDates.includes(dateStr)
      })
    }
    this.setData({ calendarDays: days })
  },

  doCheckin() {
    if (this.data.isTodayChecked) return
    app.request({
      url: `${app.globalData.apiBase}/checkin`,
      method: 'POST',
      data: {
        user_id: app.globalData.currentUser.id,
        checkin_date: this.getTodayStr()
      },
      success: (res) => {
        if (res.statusCode === 200) {
          wx.showToast({ title: '打卡成功', icon: 'success' })
          this.loadCheckins()
        }
      }
    })
  },

  prevMonth() {
    let { currentYear, currentMonth } = this.data
    if (currentMonth === 0) { currentYear--; currentMonth = 11 } 
    else currentMonth--
    this.setData({ currentYear, currentMonth }, () => this.generateCalendar())
  },

  nextMonth() {
    let { currentYear, currentMonth } = this.data
    if (currentMonth === 11) { currentYear++; currentMonth = 0 }
    else currentMonth++
    this.setData({ currentYear, currentMonth }, () => this.generateCalendar())
  }
})
