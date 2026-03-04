export interface ElectronAPI {
  minimizeWindow: () => Promise<void>
  maximizeWindow: () => Promise<void>
  closeWindow: () => Promise<void>
  hideWindow: () => Promise<void>
  getAppPath: () => Promise<string>
  sendToBackend: (message: any) => void
  onBackendMessage: (callback: (message: any) => void) => void
  onOpenSettings: (callback: () => void) => void
  removeAllListeners: (channel: string) => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export {}
