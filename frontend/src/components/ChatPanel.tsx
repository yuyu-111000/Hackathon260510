import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';

interface Props {
  history: ChatMessage[];
  onSend: (msg: string) => void;
}

export default function ChatPanel({ history, onSend }: Props) {
  const [input, setInput] = useState('');
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [history]);

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <div className="chat-section">
      <div className="chat-messages" ref={messagesRef}>
        {history.length === 0 && (
          <div style={{ color: '#666', textAlign: 'center', marginTop: '40px', fontSize: '13px' }}>
            <p>输入自然语言指令修改整合决策</p>
            <p style={{ marginTop: '8px', fontSize: '11px' }}>例如: "请保留免疫应答" 或 "为什么要合并这两个知识点"</p>
          </div>
        )}
        {history.map((msg) => (
          <div key={msg.message_id} className={`chat-msg ${msg.role}`}>
            <div className="msg-role">{msg.role === 'teacher' ? '教师' : '系统'}</div>
            <div className="msg-content">{msg.content}</div>
          </div>
        ))}
      </div>
      <div className="chat-input-box">
        <input
          placeholder="输入指令..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button className="btn btn-primary btn-sm" onClick={handleSend}>发送</button>
      </div>
    </div>
  );
}
