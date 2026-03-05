const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron')
const path = require('path')

let mainWindow = null
let tray = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 240,
    height: 260,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    fullscreenable: false,
    maximizable: false,
    minimizable: false,
    movable: true,
    // 关键设置：让窗口可穿透点击（除了交互区域）
    acceptFirstMouse: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })
  
  // 右键菜单
  const { Menu } = require('electron')
  const contextMenu = Menu.buildFromTemplate([
    { label: '显示聊天窗口', click: () => mainWindow.webContents.send('show-chat') },
    { label: '语音唤醒', click: () => mainWindow.webContents.send('wake-up') },
    { type: 'separator' },
    { label: '设置', click: () => mainWindow.webContents.send('open-settings') },
    { type: 'separator' },
    { label: '退出', click: () => { app.isQuitting = true; app.quit() } }
  ])
  
  mainWindow.webContents.on('context-menu', (event, params) => {
    contextMenu.popup(mainWindow)
  })
}

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png')
  let trayIcon
  
  try {
    trayIcon = nativeImage.createFromPath(iconPath)
    if (trayIcon.isEmpty()) {
      trayIcon = nativeImage.createEmpty()
    }
  } catch (e) {
    trayIcon = nativeImage.createEmpty()
  }

  tray = new Tray(trayIcon.resize({ width: 16, height: 16 }))

  const contextMenu = Menu.buildFromTemplate([
    { label: '显示窗口', click: () => mainWindow?.show() },
    { label: '设置', click: () => mainWindow?.webContents.send('open-settings') },
    { type: 'separator' },
    { label: '退出', click: () => { app.isQuitting = true; app.quit() } }
  ])

  tray.setToolTip('PersBot - 桌面助手')
  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => mainWindow?.show())
}

app.whenReady().then(() => {
  createWindow()
  createTray()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC Handlers
ipcMain.handle('get-app-path', () => app.getAppPath())

ipcMain.handle('minimize-window', () => mainWindow?.minimize())

ipcMain.handle('maximize-window', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})

ipcMain.handle('close-window', () => mainWindow?.hide())

ipcMain.handle('hide-window', () => mainWindow?.hide())

// 接收后端消息
ipcMain.on('backend-message', (event, message) => {
  mainWindow?.webContents.send('backend-message', message)
})
