const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // 窗口控制
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  hideWindow: () => ipcRenderer.invoke('hide-window'),
  
  // 应用路径
  getAppPath: () => ipcRenderer.invoke('get-app-path'),
  
  // 消息通信
  sendToBackend: (message) => ipcRenderer.send('to-backend', message),
  onBackendMessage: (callback) => {
    ipcRenderer.on('backend-message', (event, message) => callback(message))
  },
  onOpenSettings: (callback) => {
    ipcRenderer.on('open-settings', () => callback())
  },
  // 新增事件监听
  onShowChat: (callback) => {
    ipcRenderer.on('show-chat', () => callback())
  },
  onWakeUp: (callback) => {
    ipcRenderer.on('wake-up', () => callback())
  },
  
  // 移除监听
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel)
  }
})
