import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, RotateCcw, Trash2 } from 'lucide-react'
import { getApiError } from '../../services/apiClient'
import {
  deleteSavedInterviewAnswer,
  fetchInterviewHistoryDetail,
  retryInterviewAnswer,
} from '../../services/interviewService'

function formatScore(value) {
  const score = Number(value)
  return Number.isFinite(score) ? `${score.toFixed(1)}%` : 'Not scored'
}

function groupAnswerAttempts(answers) {
  const grouped = new Map()
  answers.forEach((answer) => {
    const question = answer.question || 'Interview question'
    if (!grouped.has(question)) grouped.set(question, [])
    grouped.get(question).push(answer)
  })
  return [...grouped.entries()]
}

export default function AnswerReview({ interviewId, token }) {
  const [open, setOpen] = useState(false)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [retryAnswerId, setRetryAnswerId] = useState(null)
  const [retryText, setRetryText] = useState('')
  const [retryError, setRetryError] = useState('')
  const [retrying, setRetrying] = useState(false)
  const [deletingAnswerId, setDeletingAnswerId] = useState(null)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    if (!open) return undefined
    let active = true
    fetchInterviewHistoryDetail({ token, interviewId })
      .then((session) => {
        if (active) setAnswers(Array.isArray(session.answers) ? session.answers : [])
      })
      .catch((error) => {
        if (active) setLoadError(getApiError(error, 'Could not load your saved answers.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [interviewId, open, token])

  const toggleReview = () => {
    if (open) {
      setOpen(false)
      return
    }
    setLoading(true)
    setLoadError('')
    setOpen(true)
  }

  const startRetry = (answer) => {
    setRetryAnswerId(answer.answer_id)
    setRetryText(answer.answer || '')
    setRetryError('')
  }

  const submitRetry = async (event, answer) => {
    event.preventDefault()
    if (!retryText.trim()) return
    setRetrying(true)
    setRetryError('')
    try {
      const attempt = await retryInterviewAnswer({
        token,
        interviewId,
        answerId: answer.answer_id,
        answer: retryText,
      })
      setAnswers((current) => [...current, attempt])
      setRetryAnswerId(null)
      setRetryText('')
    } catch (error) {
      setRetryError(getApiError(error, 'Could not evaluate your revised answer.'))
    } finally {
      setRetrying(false)
    }
  }

  const deleteAnswer = async (answer) => {
    if (!window.confirm(
      'Delete this saved answer and its feedback? The interview transcript and overall score will remain.',
    )) return
    setDeletingAnswerId(answer.answer_id)
    setDeleteError('')
    try {
      await deleteSavedInterviewAnswer({
        token,
        interviewId,
        answerId: answer.answer_id,
      })
      setAnswers((current) => current.filter(
        (item) => item.answer_id !== answer.answer_id,
      ))
      if (retryAnswerId === answer.answer_id) {
        setRetryAnswerId(null)
        setRetryText('')
      }
    } catch (error) {
      setDeleteError(getApiError(error, 'Could not delete the saved answer.'))
    } finally {
      setDeletingAnswerId(null)
    }
  }

  return (
    <section aria-labelledby="answer-review-heading" className="answer-review">
      <button
        aria-controls="answer-review-content"
        aria-expanded={open}
        className="button secondary answer-review-toggle"
        onClick={toggleReview}
        type="button"
      >
        {open ? <ChevronUp aria-hidden="true" size={17} /> : <ChevronDown aria-hidden="true" size={17} />}
        {open ? 'Hide answer review' : 'Review and retry answers'}
      </button>
      {open && (
        <div id="answer-review-content" className="answer-review-content">
          <h3 id="answer-review-heading">Your saved answers</h3>
          {loading && <p role="status">Loading your saved answers…</p>}
          {loadError && <p className="notice error" role="alert">{loadError}</p>}
          {deleteError && <p className="notice error" role="alert">{deleteError}</p>}
          {!loading && !loadError && answers.length === 0 && (
            <p className="fine-print">Your submitted answers will appear here for review.</p>
          )}
          {groupAnswerAttempts(answers).map(([question, attempts], index) => (
            <article className="answer-review-item" key={question}>
              <h4>Question {index + 1}</h4>
              <p className="answer-review-question">{question}</p>
              {attempts.map((answer, attemptIndex) => (
                <div className="answer-review-attempt" key={answer.answer_id}>
                  <div className="answer-review-heading">
                    <p className="answer-review-label">Attempt {attemptIndex + 1}</p>
                    <div className="answer-review-actions">
                      <strong>{formatScore(answer.final_score)}</strong>
                      <button
                        aria-label={`Delete saved attempt ${attemptIndex + 1}`}
                        className="button secondary answer-review-delete-button"
                        disabled={deletingAnswerId !== null || retrying}
                        onClick={() => deleteAnswer(answer)}
                        type="button"
                      >
                        <Trash2 aria-hidden="true" size={15} />
                        {deletingAnswerId === answer.answer_id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                  <p className="answer-review-label">Your answer</p>
                  <p className="answer-review-text">{answer.answer}</p>
                  {answer.feedback && (
                    <>
                      <p className="answer-review-label">Feedback</p>
                      <p className="answer-review-text">{answer.feedback}</p>
                    </>
                  )}
                  {Array.isArray(answer.missing_concepts) && answer.missing_concepts.length > 0 && (
                    <p className="fine-print">
                      Focus next: {answer.missing_concepts.join(', ')}
                    </p>
                  )}
                  {retryAnswerId === answer.answer_id ? (
                    <form className="answer-review-retry" onSubmit={(event) => submitRetry(event, answer)}>
                      <label htmlFor={`retry-answer-${answer.answer_id}`}>Revise your answer</label>
                      <textarea
                        id={`retry-answer-${answer.answer_id}`}
                        maxLength={20000}
                        onChange={(event) => setRetryText(event.target.value)}
                        required
                        rows={5}
                        value={retryText}
                      />
                      {retryError && <p className="notice error" role="alert">{retryError}</p>}
                      <div className="answer-controls">
                        <button className="button secondary" onClick={() => setRetryAnswerId(null)} type="button">
                          Cancel
                        </button>
                        <button className="button primary" disabled={retrying || !retryText.trim()} type="submit">
                          {retrying ? 'Evaluating…' : 'Submit revised answer'}
                        </button>
                      </div>
                    </form>
                  ) : (
                    <button
                      className="button secondary answer-review-retry-button"
                      disabled={deletingAnswerId !== null}
                      onClick={() => startRetry(answer)}
                      type="button"
                    >
                      <RotateCcw aria-hidden="true" size={15} />
                      Retry this answer
                    </button>
                  )}
                </div>
              ))}
            </article>
          ))}
          <p className="fine-print">
            Revised answers are saved as separate attempts and evaluated against the original question.
          </p>
        </div>
      )}
    </section>
  )
}
