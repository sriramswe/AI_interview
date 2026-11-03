import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'
import { getApiError } from '../../services/apiClient'
import {
  advanceCodingRound,
  completeCodingRoadmap,
  fetchCodingLedger,
  generateCodingRoadmap,
  requestCodingHint,
  retryCodingProblem,
  startCodingProblem,
  submitCodingSolution,
} from '../../services/interviewService'

const LANGUAGES = [
  { value: 'python', label: 'Python', monaco: 'python' },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'java', label: 'Java', monaco: 'java' },
  { value: 'cpp', label: 'C++', monaco: 'cpp' },
]

const currentRound = (ledger) => ledger?.rounds?.[String(ledger.current_round)] || null

export default function CodingSimulation({ interview, onComplete, token }) {
  const [ledger, setLedger] = useState(null)
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')
  const [explanation, setExplanation] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [latestHint, setLatestHint] = useState(null)
  const round = currentRound(ledger)
  const problem = round?.problem
  const languageConfig = LANGUAGES.find(
    (item) => item.value === (problem?.language || language),
  ) || LANGUAGES[0]

  useEffect(() => {
    let active = true
    fetchCodingLedger({ token, interviewId: interview.id })
      .then((data) => {
        if (!active) return
        const savedRound = currentRound(data)
        setLedger(data)
        setLanguage(savedRound?.language || 'python')
        setCode(savedRound?.attempts?.at(-1)?.code || savedRound?.problem?.starter_code || '')
        setExplanation(savedRound?.attempts?.at(-1)?.explanation || '')
      })
      .catch((requestError) => {
        if (!active || requestError.response?.status === 404) return
        setError(getApiError(requestError, 'Could not load the coding ledger.'))
      })
    return () => { active = false }
  }, [interview.id, token])

  const startProblem = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await startCodingProblem({ token, interviewId: interview.id, language })
      setLedger(data)
      setCode(currentRound(data)?.problem?.starter_code || '')
      setExplanation('')
      setLatestHint(null)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not generate the coding problem.'))
    } finally {
      setLoading(false)
    }
  }

  const askForHint = async () => {
    setLoading(true)
    setError('')
    try {
      const hint = await requestCodingHint({ token, interviewId: interview.id })
      setLatestHint(hint)
      setLedger((saved) => {
        const key = String(saved.current_round)
        const savedRound = saved.rounds[key]
        return {
          ...saved,
          rounds: { ...saved.rounds, [key]: { ...savedRound, hints: [...savedRound.hints, hint] } },
        }
      })
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not get a hint.'))
    } finally {
      setLoading(false)
    }
  }

  const createRoadmap = async () => {
    setLoading(true)
    setError('')
    try {
      const roadmap = await generateCodingRoadmap({ token, interviewId: interview.id })
      setLedger((saved) => {
        const key = String(saved.current_round)
        return {
          ...saved,
          rounds: { ...saved.rounds, [key]: { ...saved.rounds[key], roadmap } },
        }
      })
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not generate the learning roadmap.'))
    } finally {
      setLoading(false)
    }
  }

  const submitSolution = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setLatestHint(null)
    try {
      const result = await submitCodingSolution({
        token, interviewId: interview.id, code, explanation,
      })
      setLedger(result.ledger)
      if (result.roadmap_available) {
        try {
          const roadmap = await generateCodingRoadmap({ token, interviewId: interview.id })
          setLedger((saved) => {
            const key = String(saved.current_round)
            return {
              ...saved,
              rounds: { ...saved.rounds, [key]: { ...saved.rounds[key], roadmap } },
            }
          })
        } catch (roadmapError) {
          setError(getApiError(roadmapError, 'Your result was saved, but the roadmap could not be generated.'))
        }
      }
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not evaluate your solution.'))
    } finally {
      setLoading(false)
    }
  }

  const handleNextRound = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await advanceCodingRound({ token, interviewId: interview.id })
      setLedger(data)
      setCode(currentRound(data)?.problem?.starter_code || '')
      setExplanation('')
      setLatestHint(null)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not unlock the next round.'))
    } finally {
      setLoading(false)
    }
  }

  const handleRoadmapComplete = async () => {
    setLoading(true)
    setError('')
    try {
      await completeCodingRoadmap({ token, interviewId: interview.id })
      setLedger((saved) => {
        const key = String(saved.current_round)
        return {
          ...saved,
          rounds: { ...saved.rounds, [key]: { ...saved.rounds[key], roadmap_completed: true } },
        }
      })
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update roadmap progress.'))
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await retryCodingProblem({ token, interviewId: interview.id })
      setLedger(data)
      setCode(currentRound(data)?.problem?.starter_code || '')
      setExplanation('')
      setLatestHint(null)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not restart the challenge.'))
    } finally {
      setLoading(false)
    }
  }

  const wordCount = explanation.trim() ? explanation.trim().split(/\s+/).length : 0
  const vedaGateOpen = interview.interviewer_name?.toLowerCase() !== 'veda' || wordCount >= 12

  return (
    <section aria-labelledby="coding-title" className="coding-simulation">
      <div className="coding-heading">
        <div>
          <p className="eyebrow">Technical simulation · Coding challenge {ledger?.current_round || 1} of 2</p>
          <h2 id="coding-title">Coding challenge</h2>
        </div>
        {problem && <span className={`coding-status ${round.status}`}>{round.status.replace('_', ' ')}</span>}
      </div>
      <p className="fine-print">
        {interview.target_company
          ? `Practice tailored to ${interview.target_company} and the ${interview.sub_role} role.`
          : `Practice tailored to the ${interview.sub_role} role.`}
        {' '}This is a practice simulation, not an official company question.
      </p>

      {!problem && (
        <div className="coding-start-card">
          <label htmlFor="coding-language">Programming language</label>
          <select
            id="coding-language"
            disabled={loading || Boolean(ledger)}
            onChange={(event) => setLanguage(event.target.value)}
            value={language}
          >
            {LANGUAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <p className="fine-print">Round 2 unlocks only after a score strictly above 70% in Round 1.</p>
          {!ledger && (
            <button className="button primary" disabled={loading} onClick={startProblem} type="button">
              {loading
                ? 'Generating challenge…'
                : error ? 'Retry coding challenge' : 'Generate coding challenge'}
            </button>
          )}
        </div>
      )}

      {problem && (
        <>
          <article className="coding-problem">
            <div className="coding-problem-title">
              <div><p className="eyebrow">{problem.language} · {interview.difficulty || 'Interview'}</p><h3>{problem.title}</h3></div>
              <span>{round.attempts.length} {round.attempts.length === 1 ? 'attempt' : 'attempts'}</span>
            </div>
            <p>{problem.statement}</p>
            {problem.function_signature && <code className="coding-signature">{problem.function_signature}</code>}
            {problem.resume_skill_targets?.length > 0 && (
              <p className="fine-print">Resume skill focus: {problem.resume_skill_targets.join(' · ')}</p>
            )}
            <div className="coding-example-grid">
              {problem.examples.map((example, index) => (
                <div className="coding-example" key={`${index}-${example.input}`}>
                  <strong>Example {index + 1}</strong>
                  <p><b>Input:</b> <code>{example.input}</code></p>
                  <p><b>Output:</b> <code>{example.output}</code></p>
                  {example.explanation && <p>{example.explanation}</p>}
                </div>
              ))}
            </div>
            {problem.constraints?.length > 0 && (
              <div className="coding-constraints">
                <strong>Constraints</strong>
                <ul>{problem.constraints.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            )}
          </article>

          {round.status === 'active' && (
            <form className="coding-workbench" onSubmit={submitSolution}>
              <label htmlFor="coding-explanation">Explain your approach</label>
              <textarea
                id="coding-explanation"
                onChange={(event) => setExplanation(event.target.value)}
                placeholder="Describe the algorithm, edge cases, and time/space complexity."
                rows="4"
                value={explanation}
              />
              {interview.interviewer_name?.toLowerCase() === 'veda' && (
                <p className="fine-print">Veda’s verbalization gate: explain your approach in at least 12 words ({wordCount}/12). The editor unlocks when you finish the explanation.</p>
              )}
              <div className="coding-editor-heading">
                <label htmlFor="coding-editor">Your solution · {languageConfig.label}</label>
                <button className="button secondary" disabled={loading || round.hints.length >= 5} onClick={askForHint} type="button">
                  {loading ? 'Working…' : `Ask for hint (${round.hints.length}/5)`}
                </button>
              </div>
              <div className="coding-editor" id="coding-editor">
                <Editor
                  height="420px"
                  language={languageConfig.monaco}
                  onChange={(value) => setCode(value || '')}
                  options={{
                    automaticLayout: true,
                    fontSize: 14,
                    minimap: { enabled: false },
                    padding: { top: 16 },
                    readOnly: !vedaGateOpen,
                    scrollBeyondLastLine: false,
                    tabSize: 4,
                    wordWrap: 'on',
                  }}
                  theme="vs-dark"
                  value={code}
                />
              </div>
              {latestHint && <div className="coding-hint"><strong>Hint · Tier {latestHint.tier}</strong><p>{latestHint.hint}</p></div>}
              <button className="button primary" disabled={loading || !code.trim() || !explanation.trim() || !vedaGateOpen} type="submit">
                {loading ? 'Reviewing solution…' : 'Submit for AI review'}
              </button>
              <p className="fine-print">The AI judge does not execute code or run hidden tests; it provides a static reasoning review.</p>
            </form>
          )}

          {round.latest_evaluation && (
            <section aria-label="Coding evaluation" className="coding-evaluation">
              <div className="coding-score">
                <strong>{round.latest_evaluation.total_score}%</strong>
                <span>{round.latest_evaluation.passed ? 'Round cleared' : 'Keep practicing'}</span>
              </div>
              <div className="coding-score-grid">
                <p><b>Correctness</b><span>{round.latest_evaluation.correctness_score}%</span></p>
                <p><b>Complexity</b><span>{round.latest_evaluation.complexity_score}%</span></p>
                <p><b>Code quality</b><span>{round.latest_evaluation.quality_score}%</span></p>
              </div>
              <p>{round.latest_evaluation.correctness_feedback}</p>
              <p>{round.latest_evaluation.complexity_feedback}</p>
              <p>{round.latest_evaluation.quality_feedback}</p>
              {round.latest_evaluation.dry_run_trace.length > 0 && (
                <details>
                  <summary>AI reasoning trace · examples only</summary>
                  <ul>{round.latest_evaluation.dry_run_trace.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}</ul>
                </details>
              )}
              <p className="fine-print">{round.latest_evaluation.evaluation_notice}</p>
              {round.latest_evaluation.improvements.length > 0 && (
                <div><strong>Suggested improvements</strong><ul>{round.latest_evaluation.improvements.map((item) => <li key={item}>{item}</li>)}</ul></div>
              )}
            </section>
          )}

          {round.status === 'passed' && ledger.current_round === 1 && (
            <button className="button primary" disabled={loading} onClick={handleNextRound} type="button">
              {loading ? 'Preparing Round 2…' : 'Unlock Round 2'}
            </button>
          )}
          {ledger.status === 'completed' && (
            <div className="coding-complete">
              <p className="notice">Coding simulation complete — both rounds cleared.</p>
              {onComplete && (
                <button className="button primary" onClick={onComplete} type="button">
                  Continue to HR interview
                </button>
              )}
            </div>
          )}

          {round.status === 'failed' && (
            <section className="coding-roadmap">
              <p className="eyebrow">Learning roadmap</p>
              {!round.roadmap && (
                <button className="button secondary" disabled={loading} onClick={createRoadmap} type="button">
                  {loading ? 'Creating roadmap…' : 'Generate 7-day learning roadmap'}
                </button>
              )}
              {round.roadmap && (
                <>
                  <div className="coding-roadmap-days">
                    {round.roadmap.days.map((day) => (
                      <article key={day.day}>
                        <strong>Day {day.day} · {day.focus}</strong>
                        <ul>{day.activities.map((activity) => <li key={activity}>{activity}</li>)}</ul>
                        <p>{day.practice_prompt}</p>
                      </article>
                    ))}
                  </div>
                  {!round.roadmap_completed
                    ? <button className="button secondary" disabled={loading} onClick={handleRoadmapComplete} type="button">I’ve completed the roadmap</button>
                    : <button className="button primary" disabled={loading} onClick={handleRetry} type="button">Reattempt this challenge</button>}
                </>
              )}
            </section>
          )}
        </>
      )}
      {error && <p className="notice error" role="alert">{error}</p>}
    </section>
  )
}