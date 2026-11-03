import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  CircleHelp,
  LoaderCircle,
  Minus,
  Target,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getApiError } from '../../services/apiClient'
import {
  fetchInterviewAnalytics,
  fetchInterviewHistory,
} from '../../services/dashboardService'
import { getInterviewPath } from '../../routing/routes'

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatScore(value) {
  const score = Number(value)
  return Number.isFinite(score) ? `${score.toFixed(1)}%` : '—'
}

function ProgressMetric({ label, value, detail, icon: Icon }) {
  return (
    <article className="progress-metric">
      <span className="progress-metric-icon"><Icon aria-hidden="true" size={17} /></span>
      <span className="progress-metric-label">{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

function ScoreTrend({ sessions, unavailable }) {
  if (unavailable) {
    return (
      <div className="progress-empty-state">
        <Activity aria-hidden="true" size={20} />
        <p>Score trend is unavailable until your interview history loads.</p>
      </div>
    )
  }

  if (!sessions.length) {
    return (
      <div className="progress-empty-state">
        <Activity aria-hidden="true" size={20} />
        <p>Your score trend will appear after you complete your first practice.</p>
      </div>
    )
  }

  return (
    <div aria-label="Recent interview scores" className="score-trend">
      {sessions.map((session) => {
        const score = Number(session.average_score)
        const height = Number.isFinite(score) ? Math.min(100, Math.max(4, score)) : 4
        return (
          <div
            aria-label={`${session.role}: ${formatScore(session.average_score)} on ${formatDate(session.created_at)}`}
            className="score-trend-item"
            key={session.session_id}
            role="img"
          >
            <span className="score-trend-value">{formatScore(session.average_score)}</span>
            <div className="score-trend-track">
              <span style={{ height: `${height}%` }} />
            </div>
            <strong>{session.role}</strong>
            <small>{formatDate(session.created_at)}</small>
          </div>
        )
      })}
    </div>
  )
}

function SessionStatus({ status }) {
  const normalized = String(status || '').toLowerCase()
  const label = normalized === 'completed'
    ? 'Completed'
    : normalized === 'failed'
      ? 'Keep practicing'
      : normalized === 'in_progress'
        ? 'In progress'
        : status || 'Status unavailable'

  return <span className={`progress-status ${normalized}`}>{label}</span>
}

function RecentPractice({ history, unavailable }) {
  if (unavailable) {
    return (
      <div className="progress-empty-state compact">
        <CircleHelp aria-hidden="true" size={18} />
        <p>Recent sessions are unavailable until your interview history loads.</p>
      </div>
    )
  }

  if (!history.length) {
    return (
      <div className="progress-empty-state compact">
        <CircleHelp aria-hidden="true" size={18} />
        <p>Your completed and in-progress sessions will show up here.</p>
      </div>
    )
  }

  return (
    <ul className="recent-practice-list">
      {history.slice(0, 4).map((session) => {
        const rounds = Array.isArray(session.rounds_completed) ? session.rounds_completed : []
        const roundScores = session.round_scores && typeof session.round_scores === 'object'
          ? session.round_scores
          : {}

        return (
          <li key={session.session_id}>
            <Link
              aria-label={`Open ${session.role || 'interview practice'} session`}
              className="recent-practice-link"
              to={getInterviewPath(session.session_id)}
            >
              <div className="recent-practice-main">
                <div>
                  <strong>{session.role || 'Interview practice'}</strong>
                  <small>
                    {session.target_company ? `${session.target_company} · ` : ''}
                    {formatDate(session.created_at)}
                  </small>
                </div>
                <SessionStatus status={session.status} />
              </div>
              <div className="recent-practice-meta">
                <span>{session.total_questions || 0} answers</span>
                <span>{rounds.length} {rounds.length === 1 ? 'round' : 'rounds'} reached</span>
                {session.status === 'in_progress' && (
                  <span>
                    Question {Math.min(
                      session.questions_per_round || 20,
                      (session.questions_asked ?? 0) + 1,
                    )}/{session.questions_per_round || 20}
                  </span>
                )}
                <strong>{formatScore(session.average_score)}</strong>
              </div>
              {rounds.length > 0 && (
                <ul aria-label="Round scores" className="round-score-list">
                  {rounds.map((round) => (
                    <li key={round}>
                      <span>{round}</span>
                      <strong>
                        {Number.isFinite(Number(roundScores[round]))
                          ? `${(Number(roundScores[round]) * 10).toFixed(0)}%`
                          : 'Score unavailable'}
                      </strong>
                    </li>
                  ))}
                </ul>
              )}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

function TopicList({ title, topics, variant, unavailable }) {
  return (
    <section className={`progress-topic-card ${variant}`}>
      <h4>{title}</h4>
      {topics.length > 0
        ? (
          <ul>
            {topics.slice(0, 4).map((topic) => <li key={topic}>{topic}</li>)}
          </ul>
        )
        : <p>{unavailable
          ? 'Insights are unavailable until your analytics load.'
          : 'More scored answers will help identify this.'}</p>}
    </section>
  )
}

export default function ProgressTracker({ token }) {
  const [history, setHistory] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [analyticsError, setAnalyticsError] = useState('')

  useEffect(() => {
    let active = true

    Promise.allSettled([
      fetchInterviewHistory(token),
      fetchInterviewAnalytics(token),
    ]).then(([historyResult, analyticsResult]) => {
      if (!active) return

      if (historyResult.status === 'fulfilled') {
        setHistory(historyResult.value)
      } else {
        setHistoryError(getApiError(historyResult.reason, 'Could not load your interview history.'))
      }

      if (analyticsResult.status === 'fulfilled') {
        setAnalytics(analyticsResult.value)
      } else {
        setAnalyticsError(getApiError(analyticsResult.reason, 'Could not load your interview analytics.'))
      }
    }).finally(() => {
      if (active) setLoading(false)
    })

    return () => {
      active = false
    }
  }, [token])

  const trendSessions = useMemo(
    () => history
      .filter((session) => Number(session.total_questions) > 0)
      .slice(0, 6)
      .reverse(),
    [history],
  )
  const scoreChange = trendSessions.length > 1
    ? Number(trendSessions.at(-1).average_score) - Number(trendSessions.at(-2).average_score)
    : null
  const ScoreChangeIcon = scoreChange === null
    ? Minus
    : scoreChange > 0
      ? ArrowUpRight
      : scoreChange < 0
        ? ArrowDownRight
        : Minus

  return (
    <section aria-labelledby="progress-heading" className="progress-dashboard">
      <div className="progress-section-heading">
        <div>
          <p className="eyebrow">Your practice journey</p>
          <h2 id="progress-heading">See how you’re progressing</h2>
          <p className="muted">Every score and insight below comes from your saved interview answers.</p>
        </div>
        {loading && <LoaderCircle aria-label="Loading progress" className="resume-spinner progress-loading" size={20} />}
      </div>

      {historyError && <p className="notice" role="alert">{historyError}</p>}
      {analyticsError && <p className="notice" role="alert">{analyticsError}</p>}

      <div className="progress-metrics">
        <ProgressMetric
          detail="practice sessions"
          icon={Activity}
          label="Interviews"
          value={analytics ? analytics.total_interviews : '—'}
        />
        <ProgressMetric
          detail="across all sessions"
          icon={CheckCircle2}
          label="Answers reviewed"
          value={analytics ? analytics.total_questions_attempted : '—'}
        />
        <ProgressMetric
          detail="finished all rounds"
          icon={Target}
          label="Completed"
          value={analytics ? analytics.completed_interviews : '—'}
        />
        <ProgressMetric
          detail="completed & evaluated"
          icon={Activity}
          label="Average score"
          value={analytics ? formatScore(analytics.overall_average_score) : '—'}
        />
      </div>

      <div className="progress-content-grid">
        <section className="progress-panel">
          <div className="progress-panel-heading">
            <div>
              <h3>Score trend</h3>
              <p>Latest practice sessions with at least one evaluated answer</p>
            </div>
            <div className={`score-change ${scoreChange > 0 ? 'up' : scoreChange < 0 ? 'down' : ''}`}>
              <ScoreChangeIcon aria-hidden="true" size={16} />
              {scoreChange === null
                ? 'Need another session'
                : `${scoreChange > 0 ? '+' : ''}${scoreChange.toFixed(1)} pts vs previous`}
            </div>
          </div>
          <ScoreTrend sessions={trendSessions} unavailable={Boolean(historyError)} />
        </section>

        <section className="progress-panel">
          <div className="progress-panel-heading">
            <div>
              <h3>Recent practice</h3>
              <p>Your latest saved interview sessions</p>
            </div>
          </div>
          <RecentPractice history={history} unavailable={Boolean(historyError)} />
        </section>
      </div>

      <section className="progress-panel progress-insights">
        <div className="progress-panel-heading">
          <div>
            <h3>What to work on next</h3>
            <p>Topics are identified from repeated answer feedback.</p>
          </div>
        </div>
        <div className="progress-topics">
          <TopicList
            title="Strengths to build on"
            topics={analytics?.strengths || []}
            unavailable={Boolean(analyticsError)}
            variant="strengths"
          />
          <TopicList
            title="Practice next"
            topics={analytics?.weakest_areas || []}
            unavailable={Boolean(analyticsError)}
            variant="focus"
          />
        </div>
      </section>
    </section>
  )
}
