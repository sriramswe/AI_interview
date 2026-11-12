import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Award,
  Check,
  Code,
  Hand,
  Info,
  Loader2,
  Maximize2,
  MessageSquare,
  Mic,
  MicOff,
  PhoneOff,
  ScreenShare,
  Send,
  Sparkles,
  Subtitles,
  Trash2,
  Users,
  Video,
  VideoOff,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react'
import CodingSimulation from './CodingSimulation'
import './googleMeet.css'

export default function GoogleMeetInterview({
  interview,
  busy,
  answer,
  setAnswer,
  paymentStatus,
  handleSubmitAnswer,
  handleDeletePendingAnswer,
  handleBackToDashboard,
  lastEvaluation,
  feedbackTier,
  cameraEnabled,
  startCamera,
  stopCamera,
  micEnabled,
  startPitchAnalysis,
  stopPitchAnalysis,
  pitchRange,
  framingStatus,
  videoRef,
  speakQuestion,
  stopQuestionSpeech,
  speech,
  codingMode,
  setCodingMode,
  onSwitchToClassic,
  profile,
  token,
}) {
  const [activeDrawer, setActiveDrawer] = useState('chat') // 'chat' | 'people' | 'feedback' | 'code' | null
  const [captionsOn, setCaptionsOn] = useState(true)
  const [handRaised, setHandRaised] = useState(false)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [isSpeakingQuestion, setIsSpeakingQuestion] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [pendingAnswer, setPendingAnswer] = useState('')
  const [discardingPendingAnswer, setDiscardingPendingAnswer] = useState(false)
  const [currentTime, setCurrentTime] = useState('')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [answerStartedAt, setAnswerStartedAt] = useState(Date.now())
  const chatHistoryRef = useRef(null)
  const pendingCandidateMessageRef = useRef(null)

  const questionTotal = interview.questions_per_round || 10
  const questionsAnswered = interview.questions_asked ?? 0
  const questionNumber = Math.min(
    questionTotal,
    questionsAnswered + (interview.finished ? 0 : 1),
  )

  // Clock timer
  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      )
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  // Elapsed response timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - answerStartedAt) / 1000))
    }, 500)
    return () => clearInterval(timer)
  }, [answerStartedAt])

  useEffect(() => {
    if (activeDrawer === 'chat' && chatHistoryRef.current) {
      chatHistoryRef.current.scrollTo({
        top: chatHistoryRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [activeDrawer, chatHistory])

  useEffect(() => {
    setPendingAnswer(interview.pending_answer || '')
  }, [interview.id, interview.pending_answer])

  // Initial camera startup if not enabled
  useEffect(() => {
    if (!cameraEnabled && startCamera) {
      startCamera()
    }
  }, [cameraEnabled, startCamera])

  // Automatically read question aloud when a new question arrives
  const lastQuestionRef = useRef(null)
  useEffect(() => {
    if (
      interview?.first_question &&
      interview.first_question !== lastQuestionRef.current &&
      !interview.finished
    ) {
      lastQuestionRef.current = interview.first_question
      setAnswerStartedAt(Date.now())
      setElapsedSeconds(0)

      // Add question to meeting chat stream
      setChatHistory((prev) => [
        ...prev,
        {
          id: Date.now(),
          sender: interview.interviewer_name || 'AI Interviewer',
          role: 'interviewer',
          text: interview.first_question,
          time: new Date().toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          }),
        },
      ])

      // Auto read aloud if sound enabled
      if (soundEnabled && speakQuestion) {
        setIsSpeakingQuestion(true)
        speakQuestion(interview.first_question)
        const timeout = setTimeout(() => {
          setIsSpeakingQuestion(false)
        }, Math.min(10000, interview.first_question.length * 75))
        return () => clearTimeout(timeout)
      }
    }
  }, [interview?.first_question, interview?.finished, soundEnabled, speakQuestion])

  // Handle manual question speech replay
  const handleReplayQuestion = () => {
    if (soundEnabled && interview?.first_question && speakQuestion) {
      setIsSpeakingQuestion(true)
      speakQuestion(interview.first_question)
      setTimeout(() => setIsSpeakingQuestion(false), 6000)
    }
  }

  const toggleInterviewerMute = () => {
    if (soundEnabled) {
      stopQuestionSpeech?.()
      setIsSpeakingQuestion(false)
    }
    setSoundEnabled(!soundEnabled)
  }

  // Toggle candidate microphone / speech-to-text
  const handleToggleMic = () => {
    if (speech.listening) {
      speech.stop()
    } else {
      speech.start()
    }
  }

  // Submit Answer
  const handleSendAnswer = async (e) => {
    e?.preventDefault()
    if (!answer.trim() || busy) return

    const submittedAnswer = answer.trim()
    const durationSeconds = Math.max(
      1,
      Math.round((Date.now() - answerStartedAt) / 1000),
    )

    let messageId = pendingCandidateMessageRef.current?.id
    if (pendingCandidateMessageRef.current?.text !== submittedAnswer) {
      messageId = Date.now()
      pendingCandidateMessageRef.current = {
        id: messageId,
        text: submittedAnswer,
      }
      setChatHistory((prev) => [
        ...prev,
        {
          id: messageId,
          sender: profile?.username || 'You',
          role: 'candidate',
          text: submittedAnswer,
          deliveryStatus: 'submitting',
          time: new Date().toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          }),
        },
      ])
    } else {
      setChatHistory((prev) => prev.map((message) => (
        message.id === messageId
          ? { ...message, deliveryStatus: 'submitting' }
          : message
      )))
    }

    const submitted = await handleSubmitAnswer(answer, durationSeconds)
    if (submitted) {
      setChatHistory((prev) => prev.map((message) => (
        message.id === messageId
          ? { ...message, deliveryStatus: 'submitted' }
          : message
      )))
      pendingCandidateMessageRef.current = null
      setPendingAnswer('')
      setAnswer('')
      setHandRaised(false)
      setActiveDrawer('chat')
    } else {
      setChatHistory((prev) => prev.map((message) => (
        message.id === messageId
          ? { ...message, deliveryStatus: 'retry' }
          : message
      )))
      setPendingAnswer(submittedAnswer)
    }
  }

  const handleDiscardSavedAnswer = async () => {
    if (!pendingAnswer || busy || discardingPendingAnswer) return
    if (!window.confirm(
      'Delete the saved answer waiting for evaluation? You can submit a new answer to this question.',
    )) return
    setDiscardingPendingAnswer(true)
    try {
      const deleted = await handleDeletePendingAnswer(interview.id)
      if (!deleted) return
      const pendingMessageId = pendingCandidateMessageRef.current?.id
      setChatHistory((prev) => prev.filter(
        (message) => message.id !== pendingMessageId,
      ))
      pendingCandidateMessageRef.current = null
      setPendingAnswer('')
      setAnswer('')
    } finally {
      setDiscardingPendingAnswer(false)
    }
  }

  const formatTimer = (totalSec) => {
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  const userInitials = (profile?.username || 'Candidate')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className={`meet-container ${codingMode || interview.coding_gate_required ? 'coding-mode' : ''}`}>
      {/* Top Header Bar */}
      <header className="meet-topbar">
        <div className="meet-info-left">
          <span className="meet-status-dot" title="Live session active" />
          <h2 className="meet-title">
            {interview.role_category || 'AI Technical Assessment'} · Mock Interview
          </h2>
          <span className="meet-code">
            meet.google.com/int-{interview.id ? String(interview.id).slice(0, 6) : 'live'}
          </span>
        </div>

        <div className="meet-topbar-center">
          <span className="meet-round-pill">
            {interview.interview_round || 'Round'} · Question {questionNumber} of{' '}
            {questionTotal}
          </span>
          {interview.question_category && (
            <span className="meet-round-pill">{interview.question_category}</span>
          )}
          <span className="meet-timer-pill" title="Current answer duration">
            ⏱️ {formatTimer(elapsedSeconds)}
          </span>
        </div>

        <div className="meet-topbar-right">
          <span className="meet-clock">{currentTime}</span>
          <button
            type="button"
            className="meet-view-switch"
            onClick={onSwitchToClassic}
            title="Switch back to classic form view"
          >
            Classic View
          </button>
        </div>
      </header>

      {/* Main Video & Content Area */}
      <div className={`meet-main-area ${codingMode || interview.coding_gate_required ? 'coding-mode-active' : ''}`}>
        <div className={`meet-stage ${codingMode || interview.coding_gate_required ? 'coding-meet-stage' : ''}`}>
          {/* Coding simulation split or full grid */}
          {codingMode || interview.coding_gate_required ? (
            <div className="coding-meet-content">
              <CodingSimulation interview={interview} token={token} />
            </div>
          ) : (
            <div className="meet-grid">
              {/* Tile 1: AI Interviewer */}
              <div
                className={`meet-tile meet-ai-tile ${
                  isSpeakingQuestion ? 'speaking' : ''
                }`}
              >
                <div className="meet-tile-top-actions">
                  <span className="meet-tag-pill">Host</span>
                  <button
                    type="button"
                    className="meet-tag-pill meet-interviewer-mute"
                    aria-label={soundEnabled ? 'Mute interviewer' : 'Unmute interviewer'}
                    aria-pressed={!soundEnabled}
                    onClick={toggleInterviewerMute}
                    title={soundEnabled ? 'Mute interviewer voice' : 'Unmute interviewer voice'}
                  >
                    {soundEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
                    {soundEnabled ? 'Mute' : 'Unmute'}
                  </button>
                  {isSpeakingQuestion && (
                    <span className="meet-tag-pill" style={{ color: '#8ab4f8' }}>
                      Speaking…
                    </span>
                  )}
                </div>

                <div className="meet-avatar-wrapper">
                  <div
                    className={`meet-avatar-circle ${
                      isSpeakingQuestion ? 'pulse-speaking' : ''
                    }`}
                  >
                    <span className="meet-avatar-emoji">🤖</span>
                  </div>
                  <div className="meet-ai-status-text">
                    {interview.interviewer_name || 'AI Interviewer'}
                    {isSpeakingQuestion && (
                      <div className="meet-audio-bars">
                        <span className="meet-bar" />
                        <span className="meet-bar" />
                        <span className="meet-bar" />
                        <span className="meet-bar" />
                      </div>
                    )}
                  </div>
                </div>

                {/* Closed Captions Subtitle Box */}
                {captionsOn && !interview.finished && (
                  <div className="meet-captions-overlay">
                    <p className="meet-caption-text">
                      <span className="meet-caption-speaker">
                        {interview.interviewer_name || 'Interviewer'}:
                      </span>
                      {interview.first_question ||
                        'Hello! I am ready whenever you are.'}
                    </p>
                    <button
                      type="button"
                      className="meet-repeat-audio-btn"
                      onClick={handleReplayQuestion}
                      disabled={!soundEnabled}
                      title={soundEnabled ? 'Read question aloud again' : 'Unmute interviewer to hear the question'}
                    >
                      {soundEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
                      {soundEnabled ? 'Re-listen' : 'Interviewer muted'}
                    </button>
                  </div>
                )}

                {/* Name Badge */}
                <div className="meet-tile-name-badge">
                  <span className={`meet-mic-indicator ${soundEnabled ? 'on' : 'off'}`}>
                    {soundEnabled ? <Mic size={13} /> : <MicOff size={13} />}
                  </span>
                  <span>
                    {interview.interviewer_name || 'AI Interviewer'}
                    {!soundEnabled && ' · Muted'}
                  </span>
                </div>
              </div>

              {/* Tile 2: Candidate Webcam / Avatar */}
              <div
                className={`meet-tile meet-candidate-tile ${
                  speech.listening ? 'speaking' : ''
                }`}
              >
                <div className="meet-tile-top-actions">
                  {cameraEnabled && (
                    <span className="meet-tag-pill">{framingStatus}</span>
                  )}
                  {pitchRange && (
                    <span className="meet-tag-pill">
                      Pitch: {pitchRange.min}–{pitchRange.max} Hz
                    </span>
                  )}
                </div>

                {cameraEnabled ? (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="meet-webcam-video"
                  />
                ) : (
                  <div className="meet-cam-off-placeholder">
                    <div className="meet-user-avatar">{userInitials}</div>
                    <span className="meet-cam-off-text">Camera is off</span>
                  </div>
                )}

                {/* Interim Live Speech Transcript Bubble */}
                {speech.listening && speech.interimTranscript && (
                  <div className="meet-interim-bubble">
                    <Mic size={14} className="text-emerald" />
                    <span>Listening: {speech.interimTranscript}</span>
                  </div>
                )}

                {/* Hand raised indicator */}
                {handRaised && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '12px',
                      left: '12px',
                      background: '#fbbc04',
                      color: '#202124',
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: '700',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      zIndex: 6,
                    }}
                  >
                    <Hand size={12} /> Hand Raised
                  </div>
                )}

                {/* Candidate Name Badge */}
                <div className="meet-tile-name-badge">
                  <span
                    className={`meet-mic-indicator ${
                      speech.listening ? 'on' : 'off'
                    }`}
                  >
                    {speech.listening ? <Mic size={13} /> : <MicOff size={13} />}
                  </span>
                  <span>{profile?.username || 'You'} (Candidate)</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Collapsible Right-Side Drawer */}
        {activeDrawer && !codingMode && !interview.coding_gate_required && (
          <aside className="meet-side-drawer">
            <div className="meet-drawer-header">
              <h3>
                {activeDrawer === 'chat' && 'In-Call Messages & Answer'}
                {activeDrawer === 'people' && 'Meeting Participants'}
                {activeDrawer === 'feedback' && `${feedbackTier} AI Answer Feedback`}
                {activeDrawer === 'code' && 'Technical Workspace'}
              </h3>
              <button
                type="button"
                className="meet-drawer-close"
                onClick={() => setActiveDrawer(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="meet-drawer-tabs">
              <button
                type="button"
                className={`meet-drawer-tab ${
                  activeDrawer === 'chat' ? 'active' : ''
                }`}
                onClick={() => setActiveDrawer('chat')}
              >
                Chat & Answer
              </button>
              <button
                type="button"
                className={`meet-drawer-tab ${
                  activeDrawer === 'feedback' ? 'active' : ''
                }`}
                onClick={() => setActiveDrawer('feedback')}
              >
                Evaluation
              </button>
              <button
                type="button"
                className={`meet-drawer-tab ${
                  activeDrawer === 'people' ? 'active' : ''
                }`}
                onClick={() => setActiveDrawer('people')}
              >
                People (2)
              </button>
            </div>

            <div
              className={
                activeDrawer === 'chat'
                  ? 'meet-drawer-body chat-active'
                  : 'meet-drawer-body'
              }
            >
              {/* Chat & Answer Tab */}
              {activeDrawer === 'chat' && (
                <>
                  <div className="meet-chat-history" ref={chatHistoryRef}>
                    {chatHistory.map((msg) => (
                      <div
                        key={msg.id}
                        className={`meet-chat-msg ${msg.role}`}
                      >
                        <div className="meet-chat-sender">
                          <span>{msg.sender}</span>
                          <small>{msg.time}</small>
                        </div>
                        <div className="meet-chat-bubble">
                          {msg.role === 'candidate' && msg.text.length > 1200 ? (
                            <details className="meet-chat-long-answer">
                              <summary>
                                {msg.deliveryStatus === 'retry'
                                  ? 'Answer needs retry'
                                  : 'Your answer'}{' '}
                                · {msg.text.length.toLocaleString()} characters
                              </summary>
                              <div className="meet-chat-answer-content">{msg.text}</div>
                            </details>
                          ) : (
                            msg.text
                          )}
                          {msg.deliveryStatus && (
                            <span
                              className={`meet-chat-delivery ${msg.deliveryStatus}`}
                              role={msg.deliveryStatus === 'retry' ? 'status' : undefined}
                            >
                              {msg.deliveryStatus === 'submitting'
                                ? 'Sending…'
                                : msg.deliveryStatus === 'retry'
                                  ? 'Retry or edit answer'
                                  : 'Submitted'}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Answer Input Box */}
                  {paymentStatus && (
                    <p className="notice error" role="alert">{paymentStatus}</p>
                  )}
                  {pendingAnswer && (
                    <div className="meet-answer-retry-hint" role="status">
                      <span>
                        Your previous answer is saved and waiting for evaluation. Retry it, or edit/replace it and submit again.
                      </span>
                      <button
                        className="meet-answer-discard-btn"
                        disabled={busy || discardingPendingAnswer}
                        onClick={handleDiscardSavedAnswer}
                        type="button"
                      >
                        <Trash2 aria-hidden="true" size={14} />
                        {discardingPendingAnswer ? 'Deleting…' : 'Delete saved answer'}
                      </button>
                    </div>
                  )}
                  <form
                    onSubmit={handleSendAnswer}
                    className="meet-answer-input-box"
                  >
                    <textarea
                      rows={4}
                      value={answer}
                      readOnly={busy}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Type your answer or speak using the mic button..."
                      className="meet-answer-textarea"
                    />
                    <div className="meet-answer-footer">
                      <span>{answer.length} chars</span>
                      <button
                        type="submit"
                        disabled={busy || !answer.trim()}
                        className="meet-submit-btn"
                      >
                        {busy ? (
                          <Loader2 size={14} className="spin-icon" />
                        ) : (
                          <Send size={14} />
                        )}
                        Send Answer
                      </button>
                    </div>
                  </form>
                </>
              )}

              {/* Feedback Tab */}
              {activeDrawer === 'feedback' && (
                <>
                  {lastEvaluation ? (
                    <div className="meet-feedback-box">
                      <div className="meet-feedback-score">
                        <Award size={18} className="text-emerald" />
                        <span className="meet-score-badge">
                          Score: {lastEvaluation.score} / 10
                        </span>
                      </div>
                      <p>{lastEvaluation.feedback}</p>
                      {interview.ai_provider_status && (
                        <p className="meet-ai-provider-status">
                          Evaluated with {interview.ai_provider_status}
                        </p>
                      )}
                      {Array.isArray(lastEvaluation.strengths) && lastEvaluation.strengths.length > 0 && (
                        <div className="meet-feedback-list">
                          <strong>What went well</strong>
                          <ul>
                            {lastEvaluation.strengths.map((item, index) => (
                              <li key={`${index}-${item}`}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {Array.isArray(lastEvaluation.improvements) && lastEvaluation.improvements.length > 0 && (
                        <div className="meet-feedback-list">
                          <strong>How to improve</strong>
                          <ul>
                            {lastEvaluation.improvements.map((item, index) => (
                              <li key={`${index}-${item}`}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p style={{ color: '#9aa0a6', fontSize: '13px' }}>
                      Submit your first response to see real-time AI feedback and
                      scoring here.
                    </p>
                  )}
                </>
              )}

              {/* People Tab */}
              {activeDrawer === 'people' && (
                <div className="meet-participants-list">
                  <div className="meet-participant-row">
                    <div className="meet-participant-info">
                      <div className="meet-part-avatar ai">🤖</div>
                      <div>
                        <div className="meet-participant-name">
                          {interview.interviewer_name || 'AI Interviewer'}
                        </div>
                        <div className="meet-part-role">Meeting host</div>
                      </div>
                    </div>
                    <Mic size={15} style={{ color: '#34a853' }} />
                  </div>

                  <div className="meet-participant-row">
                    <div className="meet-participant-info">
                      <div className="meet-part-avatar user">{userInitials}</div>
                      <div>
                        <div className="meet-participant-name">
                          {profile?.username || 'Candidate'} (You)
                        </div>
                        <div className="meet-part-role">Interviewee</div>
                      </div>
                    </div>
                    {speech.listening ? (
                      <Mic size={15} style={{ color: '#34a853' }} />
                    ) : (
                      <MicOff size={15} style={{ color: '#ea4335' }} />
                    )}
                  </div>
                </div>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* Bottom Floating Google Meet Control Dock */}
      <footer className="meet-bottom-dock">
        {/* Left: Meeting details */}
        <div className="meet-dock-left">
          <span>{currentTime}</span>
          <span>|</span>
          <span>int-{interview.id ? String(interview.id).slice(0, 6) : 'prep'}</span>
        </div>

        {/* Center: Iconic Google Meet Round Buttons */}
        <div className="meet-dock-center">
          {/* Mic Button */}
          <button
            type="button"
            className={`meet-ctrl-btn ${speech.listening ? 'active' : 'danger'}`}
            onClick={handleToggleMic}
            title={speech.listening ? 'Turn microphone off' : 'Turn microphone on'}
          >
            {speech.listening ? <Mic size={20} /> : <MicOff size={20} />}
          </button>

          {/* Camera Button */}
          <button
            type="button"
            className={`meet-ctrl-btn ${cameraEnabled ? '' : 'danger'}`}
            onClick={cameraEnabled ? stopCamera : startCamera}
            title={cameraEnabled ? 'Turn camera off' : 'Turn camera on'}
          >
            {cameraEnabled ? <Video size={20} /> : <VideoOff size={20} />}
          </button>

          {/* Captions Toggle */}
          <button
            type="button"
            className={`meet-ctrl-btn ${captionsOn ? 'active' : ''}`}
            onClick={() => setCaptionsOn((c) => !c)}
            title="Toggle captions"
          >
            <Subtitles size={20} />
          </button>

          {/* Raise Hand Toggle */}
          <button
            type="button"
            className={`meet-ctrl-btn ${handRaised ? 'active' : ''}`}
            onClick={() => setHandRaised((h) => !h)}
            title="Raise hand / Ask for hint"
          >
            <Hand size={20} />
          </button>

          {/* Screen Share / Code Editor Toggle */}
          <button
            type="button"
            className={`meet-ctrl-btn ${codingMode ? 'active' : ''}`}
            onClick={() => {
              setCodingMode((current) => !current)
              setActiveDrawer(null)
            }}
            title="Screen share / Code editor"
          >
            <ScreenShare size={20} />
          </button>

          {/* Pitch Analysis Toggle */}
          <button
            type="button"
            className={`meet-ctrl-btn ${micEnabled ? 'active' : ''}`}
            onClick={micEnabled ? stopPitchAnalysis : startPitchAnalysis}
            title="Voice pitch analysis"
          >
            <Sparkles size={20} />
          </button>

          {/* End Call / Leave Button */}
          <button
            type="button"
            className="meet-leave-btn"
            onClick={handleBackToDashboard}
            title="Leave interview call"
          >
            <PhoneOff size={18} /> Leave Call
          </button>
        </div>

        {/* Right: Drawer Actions & Submit Button */}
        <div className="meet-dock-right">
          <button
            type="button"
            className={`meet-dock-icon-btn ${
              activeDrawer === 'feedback' ? 'active' : ''
            }`}
            onClick={() =>
              setActiveDrawer((curr) => (curr === 'feedback' ? null : 'feedback'))
            }
            title="Instant Evaluation"
          >
            <Award size={20} />
          </button>

          <button
            type="button"
            className={`meet-dock-icon-btn ${
              activeDrawer === 'people' ? 'active' : ''
            }`}
            onClick={() =>
              setActiveDrawer((curr) => (curr === 'people' ? null : 'people'))
            }
            title="Participants"
          >
            <Users size={20} />
          </button>

          <button
            type="button"
            className={`meet-dock-icon-btn ${
              activeDrawer === 'chat' ? 'active' : ''
            }`}
            onClick={() =>
              setActiveDrawer((curr) => (curr === 'chat' ? null : 'chat'))
            }
            title="In-call chat"
          >
            <MessageSquare size={20} />
            {answer.trim() && <span className="meet-unread-dot" />}
          </button>

          <button
            type="button"
            disabled={busy || !answer.trim()}
            onClick={handleSendAnswer}
            className="meet-submit-btn"
            title="Submit your answer to the AI interviewer"
          >
            {busy ? (
              <Loader2 size={16} className="spin-icon" />
            ) : (
              <Send size={16} />
            )}
            Submit
          </button>
        </div>
      </footer>
    </div>
  )
}
