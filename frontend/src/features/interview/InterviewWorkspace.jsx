import { useCallback, useEffect, useState } from 'react'
import { Download, Mic, MicOff, Video } from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { getApiError } from '../../services/apiClient'
import { fetchInterviewHistoryDetail } from '../../services/interviewService'
import { downloadInterviewReport } from './interviewReport'
import AnswerReview from './AnswerReview'
import CodingSimulation from './CodingSimulation'
import GoogleMeetInterview from './GoogleMeetInterview'
import { useMediaAnalysis } from './useMediaAnalysis'
import { useSpeechRecognition } from './useSpeechRecognition'

export default function InterviewWorkspace() {
  const {
    busy,
    handleBackToDashboard,
    handleCodingStageComplete,
    handleDeletePendingAnswer,
    handleGenerateRoadmap,
    handleSubmitAnswer,
    interview,
    lastEvaluation,
    paymentStatus,
    profile,
    subscription,
    token,
  } = useInterviewApp()

  const [viewMode, setViewMode] = useState('meet') // 'meet' | 'classic'
  const [codingMode, setCodingMode] = useState(false)
  const [answer, setAnswer] = useState(() => interview?.pending_answer || '')
  const [answerStartedAt, setAnswerStartedAt] = useState(null)
  const [answerDuration, setAnswerDuration] = useState(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState('')

  const questionTotal = interview.questions_per_round || 20
  const feedbackTier = !subscription || subscription.plan === 'free'
    ? 'Basic'
    : 'Detailed'
  const questionsAnswered = interview.questions_asked ?? 0
  const questionNumber = Math.min(
    questionTotal,
    questionsAnswered + (interview.finished ? 0 : 1),
  )

  const {
    cameraEnabled,
    cameraMessage,
    framingStatus,
    mediaError,
    micEnabled,
    pitchRange,
    videoRef,
    startCamera,
    stopCamera,
    startPitchAnalysis,
    stopPitchAnalysis,
    speakQuestion,
    stopQuestionSpeech,
  } = useMediaAnalysis()

  const appendTranscript = useCallback((text) => {
    setAnswer((current) => `${current}${current.trim() ? ' ' : ''}${text}`)
  }, [])
  const speech = useSpeechRecognition(appendTranscript)

  useEffect(() => {
    if (!answerStartedAt) return undefined
    const timerId = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - answerStartedAt) / 1000))
    }, 250)
    return () => window.clearInterval(timerId)
  }, [answerStartedAt])

  const startAnswerTimer = () => {
    setAnswerStartedAt(Date.now())
    setAnswerDuration(null)
    setElapsedSeconds(0)
  }

  const stopAnswerTimer = () => {
    if (answerStartedAt) {
      setAnswerDuration(Math.max(1, Math.round((Date.now() - answerStartedAt) / 1000)))
    }
    setAnswerStartedAt(null)
  }

  const toggleSpeechRecognition = () => {
    if (speech.listening) {
      speech.stop()
      stopAnswerTimer()
      return
    }

    if (!answerStartedAt) startAnswerTimer()
    speech.start()
  }

  const submitAnswer = async (event) => {
    event?.preventDefault?.()
    if (!answer.trim()) return
    const durationSeconds = answerStartedAt
      ? Math.max(1, Math.round((Date.now() - answerStartedAt) / 1000))
      : answerDuration
    setAnswerStartedAt(null)
    const submitted = await handleSubmitAnswer(answer, durationSeconds)
    if (submitted) {
      setAnswer('')
      setAnswerDuration(null)
      setElapsedSeconds(0)
    }
  }

  const handleDownloadReport = async () => {
    setReportLoading(true)
    setReportError('')
    try {
      const report = await fetchInterviewHistoryDetail({ token, interviewId: interview.id })
      downloadInterviewReport(report)
    } catch (error) {
      setReportError(getApiError(error, 'Could not prepare your interview report.'))
    } finally {
      setReportLoading(false)
    }
  }

  // If user is in Google Meet mode and interview is not yet finished, show the Google Meet interface
  if (viewMode === 'meet' && !interview.finished) {
    return (
      <section className="interview-meet-wrapper">
        <GoogleMeetInterview
          interview={interview}
          busy={busy}
          answer={answer}
          setAnswer={setAnswer}
          paymentStatus={paymentStatus}
          handleSubmitAnswer={submitAnswer}
          handleDeletePendingAnswer={handleDeletePendingAnswer}
          handleBackToDashboard={handleBackToDashboard}
          lastEvaluation={lastEvaluation}
          feedbackTier={feedbackTier}
          cameraEnabled={cameraEnabled}
          startCamera={startCamera}
          stopCamera={stopCamera}
          micEnabled={micEnabled}
          startPitchAnalysis={startPitchAnalysis}
          stopPitchAnalysis={stopPitchAnalysis}
          pitchRange={pitchRange}
          framingStatus={framingStatus}
          cameraMessage={cameraMessage}
          videoRef={videoRef}
          speakQuestion={speakQuestion}
          stopQuestionSpeech={stopQuestionSpeech}
          speech={speech}
          codingMode={codingMode}
          setCodingMode={setCodingMode}
          onSwitchToClassic={() => setViewMode('classic')}
          profile={profile}
          token={token}
        />
        <AnswerReview interviewId={interview.id} token={token} />
      </section>
    )
  }

  return (
    <section className="panel interview-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">
            {interview.coding_gate_required
              ? 'Coding stage'
              : interview.round_completed ? 'Round complete' : 'Live practice'}
          </p>
          <h2>
            {interview.finished
              ? 'Session complete'
              : interview.coding_gate_required ? 'Complete your coding assessment' : interview.first_question}
          </h2>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {!interview.finished && (
            <button
              className="button secondary"
              type="button"
              onClick={() => setViewMode('meet')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <Video size={16} /> Google Meet View
            </button>
          )}
          {!interview.finished && !interview.coding_gate_required && (
            <button className="button secondary" type="button" onClick={() => speakQuestion(interview.first_question)}>
              ▶ Read aloud
            </button>
          )}
        </div>
      </div>
      {interview.coding_gate_required ? (
        <p className="notice" role="status">
          Technical screening cleared. Complete the coding assessment to unlock your HR interview.
        </p>
      ) : (
        <div className="coding-mode-switch">
          <p className="fine-print">Choose a practice mode for this interview session.</p>
          <button
            className={codingMode ? 'button secondary' : 'button primary'}
            onClick={() => setCodingMode((current) => !current)}
            type="button"
          >
            {codingMode ? 'Return to interview' : 'Start coding simulation'}
          </button>
        </div>
      )}
      {codingMode || interview.coding_gate_required ? (
        <CodingSimulation
          interview={interview}
          onComplete={interview.coding_gate_required ? handleCodingStageComplete : undefined}
          token={token}
        />
      ) : (
        <>
      {interview.difficulty_scaled && (
        <p className="notice" role="status">
          Elite performance: the next round has been raised to difficulty {interview.difficulty_level}/5.
        </p>
      )}
      {!interview.finished && (
        <div className="interview-grid">
          <form className="answer-form" onSubmit={submitAnswer}>
            <div className="question-progress">
              <div>
                <span>{interview.interview_round || 'Interview'} · Question {questionNumber}/{questionTotal}</span>
                <strong>{Math.round((questionNumber / questionTotal) * 100)}%</strong>
              </div>
              <progress aria-label={`Question ${questionNumber} of ${questionTotal}`} max={questionTotal} value={questionNumber} />
              {interview.question_category && (
                <span className="question-category-pill">
                  {interview.question_category}
                </span>
              )}
              {interview.technical_category_plan?.length > 1 && (
                <div aria-label="Shuffled technical categories" className="question-category-list">
                  {interview.technical_category_plan.map((category) => (
                    <span
                      className={category === interview.question_category ? 'active' : ''}
                      key={category}
                    >
                      {category}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <label htmlFor="candidate-answer">Your answer</label>
            <textarea
              id="candidate-answer"
              rows="8"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="Structure your answer and include concrete examples."
            />
            <div className="speech-answer-controls">
              <button
                aria-pressed={speech.listening}
                className={speech.listening ? 'button primary' : 'button secondary'}
                disabled={!speech.speechSupported}
                onClick={toggleSpeechRecognition}
                type="button"
              >
                {speech.listening ? <MicOff aria-hidden="true" size={16} /> : <Mic aria-hidden="true" size={16} />}
                {speech.listening ? 'Stop speaking' : 'Answer by voice'}
              </button>
              <span className="fine-print">
                {speech.speechSupported
                  ? 'Speech is transcribed by your browser; only submitted text is sent to InterviewAI.'
                  : 'Speech recognition is not supported by this browser.'}
              </span>
            </div>
            {speech.interimTranscript && (
              <p aria-live="polite" className="speech-interim">
                Listening: {speech.interimTranscript}
              </p>
            )}
            {speech.speechError && <p className="notice error" role="alert">{speech.speechError}</p>}
            <div className="answer-controls">
              <span className="timer">
                {String(Math.floor(elapsedSeconds / 60)).padStart(2, '0')}:
                {String(elapsedSeconds % 60).padStart(2, '0')}
              </span>
              {answerStartedAt
                ? <button className="button secondary" type="button" onClick={stopAnswerTimer}>Finish response</button>
                : <button className="button secondary" type="button" onClick={startAnswerTimer}>Start response timer</button>}
              <button className="button primary" disabled={busy || !answer.trim()} type="submit">
                {busy ? 'Evaluating…' : 'Submit answer'}
              </button>
            </div>
            <p className="fine-print">The timer is optional. Its duration is sent with your answer only when you start it.</p>
          </form>

          <aside className="media-card">
            <video
              ref={videoRef}
              className={cameraEnabled ? 'camera-preview active' : 'camera-preview'}
              autoPlay
              playsInline
              muted
              aria-label="Private camera preview"
            />
            {!cameraEnabled && (
              <div className="camera-placeholder"><span>◉</span><p>Camera preview stays on this device.</p></div>
            )}
            <div className="media-controls">
              {cameraEnabled
                ? <button className="button secondary" type="button" onClick={stopCamera}>Turn camera off</button>
                : <button className="button secondary" type="button" onClick={startCamera}>Enable camera</button>}
              {micEnabled
                ? <button className="button secondary" type="button" onClick={stopPitchAnalysis}>Stop pitch check</button>
                : <button className="button secondary" type="button" onClick={startPitchAnalysis}>Check voice pitch</button>}
            </div>
            <p className="fine-print">{cameraMessage}</p>
            {mediaError && <p className="notice error" role="status">{mediaError}</p>}
            {cameraEnabled && <p className="metric-note">{framingStatus}</p>}
            {pitchRange && (
              <p className="metric-note">
                Observed pitch range: {pitchRange.min}–{pitchRange.max} Hz. No voice recording is saved.
              </p>
            )}
            <p className="fine-print">Camera framing and pitch are estimates, not emotion, confidence, or body-language judgments.</p>
          </aside>
        </div>
      )}
      {lastEvaluation && (
        <div className="feedback-card">
          <p className="eyebrow">{feedbackTier} answer feedback · {lastEvaluation.score}/10</p>
          <p>{lastEvaluation.feedback}</p>
          {interview.ai_provider_status && (
            <p className="fine-print">Evaluation model: {interview.ai_provider_status}</p>
          )}
          {Array.isArray(lastEvaluation.strengths) && lastEvaluation.strengths.length > 0 && (
            <div className="hiring-report-list">
              <strong>What went well</strong>
              <ul>
                {lastEvaluation.strengths.map((item, index) => (
                  <li key={`${index}-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {Array.isArray(lastEvaluation.improvements) && lastEvaluation.improvements.length > 0 && (
            <div className="hiring-report-list">
              <strong>How to improve</strong>
              <ul>
                {lastEvaluation.improvements.map((item, index) => (
                  <li key={`${index}-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {lastEvaluation.vibe_assessment && <p className="fine-print">Vibe assessment is available in interview analytics.</p>}
        </div>
      )}
      <AnswerReview interviewId={interview.id} token={token} />
      {interview.finished && (
        <div className="feedback-card">
          <p className="eyebrow">
            {interview.master_report_pending
              ? `Score outcome: ${interview.selection_status || 'completed'} · scorecard pending`
              : interview.overall_status === 'failed'
                ? 'Score outcome · Practice simulation only'
                : 'Score outcome · Practice simulation only'}
          </p>
          <h3 className="hiring-verdict">
            {interview.master_report_pending
              ? interview.selection_status === 'selected'
                ? 'Selected'
                : 'Interview rounds completed'
              : interview.overall_status === 'failed'
                ? `Failed${interview.failed_round ? ` · ${interview.failed_round}` : ''}`
                : interview.selection_status === 'selected'
                  ? 'Selected'
                  : interview.master_report?.final_verdict || 'Interview complete'}
          </h3>
          {interview.selection_score !== null && interview.selection_score !== undefined && (
            <p>Score-based result: {interview.selection_score}/10</p>
          )}
          {interview.master_report?.overall_score !== undefined && (
            <p>AI scorecard overall score: {interview.master_report.overall_score}/10</p>
          )}
          {interview.master_report?.final_verdict && (
            <p>AI scorecard verdict: {interview.master_report.final_verdict}</p>
          )}
          {interview.report_provider_status && (
            <p className="fine-print">Final scorecard: {interview.report_provider_status}</p>
          )}
          <p>
            {interview.overall_message
              || interview.master_report?.recruiter_closing_note
              || 'Your interview session is complete.'}
          </p>
          {interview.master_report_pending && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => handleSubmitAnswer(interview.final_answer)}
              type="button"
            >
              {busy ? 'Retrying scorecard…' : 'Retry final scorecard'}
            </button>
          )}
          {interview.master_report?.strengths?.length > 0 && (
            <div className="hiring-report-list">
              <strong>Strengths</strong>
              <ul>{interview.master_report.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          )}
          {interview.master_report?.areas_to_improve?.length > 0 && (
            <div className="hiring-report-list">
              <strong>Development areas</strong>
              <ul>{interview.master_report.areas_to_improve.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          )}
          {subscription?.plan === 'elite' && (
            <button className="button secondary" type="button" onClick={handleGenerateRoadmap}>
              Generate 7-day learning roadmap
            </button>
          )}
          <button
            className="button secondary"
            disabled={reportLoading}
            onClick={handleDownloadReport}
            type="button"
          >
            <Download aria-hidden="true" size={16} />
            {reportLoading ? 'Preparing report…' : 'Download performance report'}
          </button>
          {reportError && <p className="notice error" role="alert">{reportError}</p>}
        </div>
      )}
      {paymentStatus && <p className="notice" role="status">{paymentStatus}</p>}
      <button className="text-button" type="button" onClick={handleBackToDashboard}>Back to dashboard</button>
        </>
      )}
    </section>
  )
}
