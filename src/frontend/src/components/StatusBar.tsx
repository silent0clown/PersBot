import { BotState } from '../App'
import './StatusBar.css'

interface StatusBarProps {
  isConnected: boolean
  state: BotState
  onMinimize: () => void
  onClose: () => void
}

export default function StatusBar({ isConnected, onMinimize, onClose }: StatusBarProps) {
  return (
    <div className="status-bar no-drag">
      <div className="status-left">
        <div className={`connection-dot ${isConnected ? 'connected' : ''}`} />
        <span className="status-text">
          {isConnected ? '已连接' : '未连接'}
        </span>
      </div>
      
      <div className="window-controls">
        <button className="control-btn minimize" onClick={onMinimize} title="最小化">
          <svg width="12" height="12" viewBox="0 0 12 12">
            <rect y="5" width="12" height="2" fill="currentColor" />
          </svg>
        </button>
        <button className="control-btn close" onClick={onClose} title="隐藏">
          <svg width="12" height="12" viewBox="0 0 12 12">
            <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" strokeWidth="2" />
          </svg>
        </button>
      </div>
    </div>
  )
}
