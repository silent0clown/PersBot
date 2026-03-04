import { useState } from 'react'
import { BotMessage, BotState } from '../App'
import './ControlPanel.css'

interface ControlPanelProps {
  messages: BotMessage[]
  onSendMessage: (content: string) => void
  botState: BotState
}

export default function ControlPanel({ messages, onSendMessage, botState }: ControlPanelProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      onSendMessage(input.trim())
      setInput('')
    }
  }

  return (
    <div className="control-panel">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>你好！我是 PersBot</p>
            <p>可以语音唤醒我，或者直接打字聊天</p>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-content">{msg.content}</div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          disabled={botState !== 'idle' && botState !== 'speaking'}
        />
        <button type="submit" disabled={!input.trim() || botState !== 'idle'}>
          发送
        </button>
      </form>

      <div className="quick-actions">
        <button onClick={() => onSendMessage('打开微信')}>打开微信</button>
        <button onClick={() => onSendMessage('打开浏览器')}>打开浏览器</button>
        <button onClick={() => onSendMessage('截图')}>截图</button>
      </div>
    </div>
  )
}
