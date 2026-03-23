import { useState, useEffect, useRef } from 'react'
import BotAvatar from './components/BotAvatar'
import StatusBar from './components/StatusBar'
import './App.css'

export type BotState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error'

export interface BotMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

function App() {
  const [botState, setBotState] = useState<BotState>('idle')
  const [messages, setMessages] = useState<BotMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [input, setInput] = useState('')
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isDevelopmentMode = process.env.NODE_ENV === 'development';
  
  // 滚动到最新消息
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  // 语音播放功能
  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      setIsPlayingAudio(true);
      const utterance = new SpeechSynthesisUtterance(text);
      
      utterance.onend = () => {
        setIsPlayingAudio(false);
      };
      
      utterance.onerror = () => {
        setIsPlayingAudio(false);
      };
      
      speechSynthesis.speak(utterance);
    } else {
      console.warn('浏览器不支持语音合成功能');
      setIsPlayingAudio(false);
    }
  };
  
  // 复制消息内容
  const copyMessage = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // 可以添加一个提示，显示复制成功
      console.log('复制成功');
    }).catch(err => {
      console.error('复制失败：', err);
    });
  };

  useEffect(() => {
    // 连接后端 WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onopen = () => {
      console.log('Connected to backend')
      setIsConnected(true)
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleBackendMessage(data)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
    
    ws.onclose = () => {
      setIsConnected(false)
    }

    // Electron IPC 监听
    if (window.electronAPI) {
      window.electronAPI.onBackendMessage((message: any) => {
        handleBackendMessage(message)
      })
      
      window.electronAPI.onOpenSettings(() => {
        console.log('Settings opened')
      })
      
      // @ts-ignore
      if (window.electronAPI.onShowChat) {
        // @ts-ignore
        window.electronAPI.onShowChat(() => {
          console.log('Show chat requested')
        })
      }
      
      // @ts-ignore
      if (window.electronAPI.onWakeUp) {
        // @ts-ignore
        window.electronAPI.onWakeUp(() => {
          setBotState('listening')
          setTimeout(() => setBotState('idle'), 2000)
        })
      }
    }

    return () => {
      ws.close()
    }
  }, [])

  const handleBackendMessage = (data: any) => {
    console.log('Received backend message:', data)
    switch (data.type) {
      case 'wake_word':
        setBotState('listening')
        break
      case 'listening':
        setBotState('listening')
        break
      case 'thinking':
        setBotState('thinking')
        break
      case 'speaking':
        setBotState('speaking')
        break
      case 'idle':
        setBotState('idle')
        break
      case 'error':
        setBotState('error')
        break
      case 'response':
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.content,
          timestamp: Date.now()
        }])
        break
      default:
        // 处理普通文本消息
        if (typeof data === 'string') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: data,
            timestamp: Date.now()
          }])
        } else if (data && typeof data.content === 'string') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.content,
            timestamp: Date.now()
          }])
        }
        break
    }
  }

  const sendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage = {
      id: Date.now().toString(),
      role: 'user' as const,
      content,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMessage])
    
    try {
      // 发送请求并等待响应
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content })
      })
      
      if (!response.ok) throw new Error('Request failed')

    } catch (error) {
      console.error('Failed to send message:', error)
      // 可选：添加错误消息到聊天列表
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant' as const,
        content: '抱歉，我暂时无法回答这个问题。',
        timestamp: Date.now()
      }])
    }
  }

  const isElectron = !!window.electronAPI
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      sendMessage(input.trim())
      setInput('')
    }
  }

  return (
    <div className={`app-container ${isElectron ? 'electron' : ''}`}>
      <StatusBar 
        isConnected={isConnected} 
        state={botState}
        onMinimize={() => window.electronAPI?.minimizeWindow()}
        onClose={() => window.electronAPI?.hideWindow()}
      />
      
      <main className={`main-content ${isDevelopmentMode ? 'development' : 'desktop'}`}>
        {/* 左侧：AI宠物区域 */}
        <div className="pet-area">
          <BotAvatar state={botState} />
        </div>
        
        {/* 右侧：聊天对话框区域 */}
        <div className="chat-area">
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="empty-state">
                <p>你好！我是 PersBot</p>
                <p>可以语音唤醒我，或者直接打字聊天</p>
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className={`message ${msg.role}`}>
                  <div className={`message-header ${msg.role}`}>
                    <div className="sender-info">
                      <span className="sender">{msg.role === 'user' ? '我' : 'PersBot'}</span>
                      <span className="message-timestamp">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {/* 播放按钮移动到角色名字后面 */}
                      {msg.role === 'assistant' && (
                        <button 
                          className="header-speak-btn" 
                          onClick={() => speakText(msg.content)}
                          title="播放语音"
                        >
                          🔊
                        </button>
                      )}
                    </div>
                  </div>
                  {/* 移除 onClick 触发 speakText，让文字可以自由选择 */}
                  <div className="message-content">
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入框始终保持在底部 */}
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入消息..."
              disabled={botState === 'error'}
            />
            <button type="submit" disabled={!input.trim() || isPlayingAudio}>
              发送
            </button>
          </form>

          <div className="quick-actions">
            <button onClick={() => sendMessage('打开微信')}>打开微信</button>
            <button onClick={() => sendMessage('打开浏览器')}>打开浏览器</button>
            <button onClick={() => sendMessage('截图')}>截图</button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
