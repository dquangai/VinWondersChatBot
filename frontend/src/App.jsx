import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    { 
      role: 'bot', 
      text: 'Chào bạn! Tôi là linh vật hướng dẫn viên của VinWonders. Bạn muốn tìm hiểu về địa điểm nào, hay cần lên lịch trình vui chơi trong ngày hôm nay?' 
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [locationData, setLocationData] = useState(null)
  
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return
    
    const userMsg = input.trim()
    setMessages(prev => [...prev, { role: 'user', text: userMsg }])
    setInput('')
    setLoading(true)

    try {
      // Build history string from previous messages (excluding the first greeting)
      const historyStr = messages.slice(1).map(m => `${m.role === 'user' ? 'User' : 'Agent'}: ${m.text}`).join('\n')

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, history: historyStr })
      })

      const data = await response.json()
      
      setMessages(prev => [...prev, { role: 'bot', text: data.reply }])
      
      if (data.location) {
        setLocationData(data.location)
      }
    } catch (error) {
      console.error(error)
      setMessages(prev => [...prev, { role: 'bot', text: 'Xin lỗi, đã có lỗi kết nối đến máy chủ.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="logo-area">
          <div className="logo-icon">🚀</div>
          <div className="logo-text">ViVu AI</div>
        </div>
        
        <div className="sidebar-section">
          <div className="section-title">🕒 LỊCH SỬ TRÒ CHUYỆN</div>
          <div className="history-item active">
            <span className="icon">💬</span> Khám phá VinWonders
          </div>
          <div className="history-item">
            <span className="icon">💬</span> Lịch trình đi Nha Trang
          </div>
        </div>
        
        <div className="sidebar-section">
          <div className="section-title">📌 CHUYẾN ĐI ĐÃ LƯU</div>
          <div className="history-item">
            <span className="icon">✈️</span> Phú Quốc nghỉ dưỡng
          </div>
        </div>
      </div>

      {/* MAIN CHAT */}
      <div className="main-chat">
        <div className="messages-area">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              {msg.role === 'bot' && <div className="avatar bot-avatar">🤖</div>}
              <div className="message-bubble">{msg.text}</div>
              {msg.role === 'user' && <div className="avatar user-avatar">👤</div>}
            </div>
          ))}
          {loading && (
            <div className="message-wrapper bot">
              <div className="avatar bot-avatar">🤖</div>
              <div className="message-bubble typing">Đang suy nghĩ...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="input-area">
          <div className="input-box">
            <input 
              type="text" 
              placeholder="Hỏi bất cứ điều gì về chuyến đi của bạn..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={handleSend} disabled={loading} className="send-btn">
              ➤
            </button>
          </div>
        </div>
      </div>

      {/* DETAILS PANEL */}
      <div className="details-panel">
        <div className="panel-header">📍 VỊ TRÍ ĐỀ XUẤT</div>
        
        {locationData ? (
          <div className="location-card">
            <div className="main-image-container">
              <img src={locationData.images[0]} alt={locationData.name} className="main-image" />
              <div className="location-pin">📍</div>
            </div>
            
            <div className="images-grid">
              {locationData.images.slice(1).map((img, i) => (
                <img key={i} src={img} alt="Thumb" className="thumb-image" />
              ))}
            </div>
            
            <div className="location-info">
              <h2>{locationData.name}</h2>
              <div className="rating">⭐⭐⭐⭐⭐ {locationData.rating} ({locationData.reviews})</div>
              <div className="details-row">
                <span>🕒 {locationData.time}</span>
                <span>🎟️ {locationData.price}</span>
              </div>
              <p className="description">{locationData.description}</p>
              <button className="book-btn">Đặt Vé Ngay ➤</button>
            </div>
          </div>
        ) : (
          <div className="empty-panel">
            <div className="empty-icon">🗺️</div>
            <p>Chưa có địa điểm nào được gợi ý.</p>
            <p className="sub-text">Hãy hỏi Chatbot về một điểm đến bất kỳ!</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
