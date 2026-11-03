import { useEffect, useRef, useState } from 'react'
import { Bot, MessageCircle, Send, X } from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { getApiError } from '../../services/apiClient'
import { askProjectHelp } from '../../services/projectHelpService'
import './projectHelpChat.css'

export default function ProjectHelpChat() {
  const { profile, token } = useInterviewApp()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const messageListRef = useRef(null)

  useEffect(() => {
    messageListRef.current?.scrollTo({
      top: messageListRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, open])

  if (!token || !profile) return null

  const sendMessage = async (event) => {
    event.preventDefault()
    const cleanMessage = message.trim()
    if (!cleanMessage || sending) return

    setError('')
    setSending(true)
    setMessage('')
    try {
      const answer = await askProjectHelp({
        token,
        message: cleanMessage,
        history: messages.slice(-10).map((turn) => ({
          ...turn,
          content: turn.content.slice(-2000),
        })),
      })
      setMessages((current) => [
        ...current,
        { role: 'user', content: cleanMessage },
        { role: 'assistant', content: answer },
      ])
    } catch (requestError) {
      setMessages((current) => [
        ...current,
        { role: 'user', content: cleanMessage },
      ])
      setError(getApiError(requestError, 'Project help could not respond. Please try again.'))
    } finally {
      setSending(false)
    }
  }

  return (
    <aside className="project-chat" aria-label="Project help assistant">
      {open && (
        <section className="project-chat-panel" aria-labelledby="project-chat-title">
          <header className="project-chat-header">
            <span className="project-chat-icon"><Bot size={19} aria-hidden="true" /></span>
            <div>
              <h2 id="project-chat-title">InterviewAI help</h2>
              <p>Ask about features, plans, or setup</p>
            </div>
            <button
              aria-label="Close project help"
              className="project-chat-close"
              onClick={() => setOpen(false)}
              type="button"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </header>
          <div className="project-chat-messages" ref={messageListRef} aria-live="polite">
            {messages.length === 0 && (
              <p className="project-chat-intro">
                I can explain how this project works. I can’t access accounts or change payments.
              </p>
            )}
            {messages.map((turn, index) => (
              <p className={`project-chat-message ${turn.role}`} key={`${index}-${turn.role}`}>
                {turn.content}
              </p>
            ))}
            {sending && <p className="project-chat-status" role="status">Thinking…</p>}
            {error && <p className="project-chat-error" role="alert">{error}</p>}
          </div>
          <form className="project-chat-form" onSubmit={sendMessage}>
            <label className="sr-only" htmlFor="project-chat-input">Ask about InterviewAI</label>
            <input
              autoComplete="off"
              id="project-chat-input"
              maxLength={5000}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask a project question…"
              value={message}
            />
            <button aria-label="Send message" disabled={!message.trim() || sending} type="submit">
              <Send size={17} aria-hidden="true" />
            </button>
          </form>
        </section>
      )}
      <button
        aria-expanded={open}
        aria-label={open ? 'Close project help' : 'Open project help'}
        className="project-chat-toggle"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        {open ? <X size={21} aria-hidden="true" /> : <MessageCircle size={21} aria-hidden="true" />}
      </button>
    </aside>
  )
}
