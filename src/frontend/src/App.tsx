import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import BotAvatar from './components/BotAvatar'
import ControlPanel from './components/ControlPanel'
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
      
      window.electronAPI.onShowChat(() => {
        console.log('Show chat requested')
      })
      
      window.electronAPI.onWakeUp(() => {
        setBotState('listening')
        setTimeout(() => setBotState('idle'), 2000)
      })
    }

    return () => {
      ws.close()
    }
  }, [])

  const handleBackendMessage = (data: any) => {
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
    }
  }

  const sendMessage = (content: string) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now()
    }])
    
    // 发送到后端
    fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: content })
    }).catch(console.error)
  }

  return (
    <div className="app-container">
      <StatusBar 
        isConnected={isConnected} 
        state={botState}
        onMinimize={() => window.electronAPI?.minimizeWindow()}
        onClose={() => window.electronAPI?.hideWindow()}
      />
      
      <main className="main-content">
        <BotAvatar state={botState} />
        
        <ControlPanel 
          messages={messages}
          onSendMessage={sendMessage}
          botState={botState}
        />
      </main>
    </div>
  )
}

export default App
