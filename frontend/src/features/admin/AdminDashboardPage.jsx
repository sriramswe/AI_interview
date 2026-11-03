import { useEffect, useState } from 'react'
import { Check, ExternalLink, RefreshCw, Search, ShieldAlert, Trash2, X } from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { getApiError } from '../../services/apiClient'
import {
  deleteAdminUser,
  fetchAdminSummary,
  fetchAdminUsers,
  fetchPaymentReceipt,
  fetchPendingPayments,
  reviewPayment,
  updateAdminUser,
} from '../../services/adminService'
import { AppHeader } from '../dashboard/DashboardPage'
import './adminDashboard.css'

const EMPTY_SUMMARY = {
  total_users: 0,
  active_subscriptions: 0,
  pending_payments: 0,
  saved_resumes: 0,
}

export default function AdminDashboardPage() {
  const { profile, token } = useInterviewApp()
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [users, setUsers] = useState([])
  const [totalUsers, setTotalUsers] = useState(0)
  const [payments, setPayments] = useState([])
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [planDrafts, setPlanDrafts] = useState({})
  const [roleDrafts, setRoleDrafts] = useState({})
  const [durationDays, setDurationDays] = useState('30')
  const [reviewNote, setReviewNote] = useState('')
  const [receipt, setReceipt] = useState(null)
  const [busy, setBusy] = useState(false)
  const [busyUser, setBusyUser] = useState(null)
  const [busyPayment, setBusyPayment] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const pageSize = 50

  useEffect(() => {
    let active = true
    Promise.allSettled([
      fetchAdminSummary(token),
      fetchAdminUsers({ token, search, offset: page * pageSize, limit: pageSize }),
      fetchPendingPayments(token),
    ]).then(([summaryResult, usersResult, paymentsResult]) => {
      if (!active) return
      const failures = []
      if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value)
      else failures.push(getApiError(summaryResult.reason, 'Could not load admin summary.'))
      if (usersResult.status === 'fulfilled') {
        setUsers(usersResult.value.users)
        setTotalUsers(usersResult.value.total)
        setPlanDrafts(Object.fromEntries(
          usersResult.value.users.map((user) => [user.id, user.plan]),
        ))
        setRoleDrafts(Object.fromEntries(
          usersResult.value.users.map((user) => [user.id, user.role]),
        ))
      } else failures.push(getApiError(usersResult.reason, 'Could not load users.'))
      if (paymentsResult.status === 'fulfilled') setPayments(paymentsResult.value)
      else failures.push(getApiError(paymentsResult.reason, 'Could not load pending payments.'))
      setError(failures.join(' '))
      setBusy(false)
    })
    return () => {
      active = false
    }
  }, [page, refreshKey, search, token])

  useEffect(() => () => {
    if (receipt?.url) URL.revokeObjectURL(receipt.url)
  }, [receipt?.url])

  const handleUserUpdate = async (user, updates, successMessage) => {
    setBusyUser(user.id)
    setError('')
    setNotice('')
    try {
      const updated = await updateAdminUser({
        token,
        userId: user.id,
        updates,
      })
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item))
      setPlanDrafts((current) => ({ ...current, [updated.id]: updated.plan }))
      setRoleDrafts((current) => ({ ...current, [updated.id]: updated.role }))
      setNotice(successMessage)
      const updatedSummary = await fetchAdminSummary(token)
      setSummary(updatedSummary)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not update this account.'))
    } finally {
      setBusyUser(null)
    }
  }

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`Permanently delete ${user.email} and their account data? This cannot be undone.`)) {
      return
    }
    setBusyUser(user.id)
    setError('')
    setNotice('')
    try {
      await deleteAdminUser({ token, userId: user.id })
      setUsers((current) => current.filter((item) => item.id !== user.id))
      setTotalUsers((current) => Math.max(0, current - 1))
      setNotice(`Deleted ${user.email}.`)
      setSummary(await fetchAdminSummary(token))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not delete this account.'))
    } finally {
      setBusyUser(null)
    }
  }

  const handlePaymentReview = async (payment, decision) => {
    setBusyPayment(payment.payment_id)
    setError('')
    setNotice('')
    try {
      await reviewPayment({
        token,
        paymentId: payment.payment_id,
        decision,
        reviewNote: reviewNote.trim() || null,
      })
      setPayments((current) => current.filter(
        (item) => item.payment_id !== payment.payment_id,
      ))
      setReviewNote('')
      setNotice(`Payment ${payment.payment_id} ${decision}.`)
      setSummary(await fetchAdminSummary(token))
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not review this payment.'))
    } finally {
      setBusyPayment(null)
    }
  }

  const handleReceipt = async (payment) => {
    setError('')
    try {
      const blob = await fetchPaymentReceipt({
        token,
        paymentId: payment.payment_id,
      })
      setReceipt({
        id: payment.payment_id,
        url: URL.createObjectURL(blob),
        type: blob.type,
      })
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load this payment receipt.'))
    }
  }

  return (
    <main className="page-shell">
      <AppHeader />
      <section className="admin-hero">
        <div>
          <p className="eyebrow">Restricted operations</p>
          <h1>Super-admin console</h1>
          <p className="muted">Manage user access, subscriptions, and payment reviews.</p>
        </div>
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => {
            setBusy(true)
            setRefreshKey((key) => key + 1)
          }}
          type="button"
        >
          <RefreshCw aria-hidden="true" size={16} /> Refresh
        </button>
      </section>

      {error && <p className="notice error" role="alert">{error}</p>}
      {notice && <p className="notice success" role="status">{notice}</p>}

      <section aria-label="Platform summary" className="admin-summary-grid">
        {[
          ['Users', summary.total_users],
          ['Active subscriptions', summary.active_subscriptions],
          ['Pending payments', summary.pending_payments],
          ['Saved resumes', summary.saved_resumes],
        ].map(([label, value]) => (
          <article className="panel admin-stat" key={label}>
            <p>{label}</p>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section aria-labelledby="admin-users-title" className="panel admin-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Account access</p>
            <h2 id="admin-users-title">Users</h2>
          </div>
          <span className="muted">{totalUsers} total</span>
        </div>
        <form
          className="admin-search"
          onSubmit={(event) => {
            event.preventDefault()
            setPage(0)
            const nextSearch = searchInput.trim()
            if (nextSearch === search && page === 0) setRefreshKey((key) => key + 1)
            else setSearch(nextSearch)
          }}
        >
          <label className="sr-only" htmlFor="admin-user-search">Search users</label>
          <Search aria-hidden="true" size={17} />
          <input
            id="admin-user-search"
            maxLength={120}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search by name or email"
            value={searchInput}
          />
          <button className="button secondary" disabled={busy} type="submit">Search</button>
        </form>

        <div className="admin-table-scroll">
          <table className="admin-table">
            <thead>
              <tr><th>User</th><th>Status</th><th>Plan</th><th>Role and manage</th></tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>
                    <strong>{user.username}</strong>
                    <span>{user.email}</span>
                    <small>Role: {user.role}</small>
                    <small>
                      Gender: {
                        user.gender
                          ? user.gender.replaceAll('_', ' ')
                          : 'Not provided'
                      }
                    </small>
                    <small>Joined {new Date(user.created_at).toLocaleDateString()}</small>
                  </td>
                  <td>
                    <span className={`admin-status ${user.suspended ? 'suspended' : 'active'}`}>
                      {user.suspended ? 'Suspended' : 'Active'}
                    </span>
                    {user.super_admin && <small className="admin-protected"><ShieldAlert size={13} /> Super admin</small>}
                  </td>
                  <td>
                    <strong className="admin-plan">
                      {user.plan === 'legacy_resume' ? 'Legacy resume' : user.plan}
                    </strong>
                    {user.subscription_expires_at && (
                      <small>Until {new Date(user.subscription_expires_at).toLocaleDateString()}</small>
                    )}
                  </td>
                  <td>
                    <div className="admin-user-actions">
                      {profile?.is_super_admin && (
                        <div className="admin-plan-action">
                          <label className="sr-only" htmlFor={`role-${user.id}`}>
                            Role for {user.email}
                          </label>
                          <select
                            disabled={Boolean(busyUser) || user.super_admin}
                            id={`role-${user.id}`}
                            onChange={(event) => setRoleDrafts((current) => ({
                              ...current,
                              [user.id]: event.target.value,
                            }))}
                            value={roleDrafts[user.id] || user.role}
                          >
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                          </select>
                          <button
                            aria-label={`Save role for ${user.email}`}
                            disabled={Boolean(busyUser)
                              || user.super_admin
                              || roleDrafts[user.id] === user.role}
                            onClick={() => handleUserUpdate(
                              user,
                              { role: roleDrafts[user.id] },
                              `Updated ${user.email}'s role.`,
                            )}
                            type="button"
                          >
                            <Check size={15} aria-hidden="true" />
                          </button>
                        </div>
                      )}
                      <div className="admin-plan-action">
                        <label className="sr-only" htmlFor={`plan-${user.id}`}>Plan for {user.email}</label>
                        <select
                          disabled={Boolean(busyUser) || user.super_admin}
                          id={`plan-${user.id}`}
                          onChange={(event) => setPlanDrafts((current) => ({
                            ...current,
                            [user.id]: event.target.value,
                          }))}
                          value={planDrafts[user.id] || user.plan}
                        >
                          <option value="free">Free</option>
                          <option value="pro">Pro</option>
                          {user.plan === 'legacy_resume' && (
                            <option disabled value="legacy_resume">Legacy resume (existing)</option>
                          )}
                          <option value="elite">Elite</option>
                        </select>
                        <button
                          aria-label={`Save plan for ${user.email}`}
                          disabled={Boolean(busyUser)
                            || user.super_admin
                            || planDrafts[user.id] === user.plan
                            || Number(durationDays) < 1
                            || Number(durationDays) > 3650}
                          onClick={() => handleUserUpdate(
                            user,
                            { plan: planDrafts[user.id], duration_days: Number(durationDays) },
                            `Updated ${user.email}'s plan.`,
                          )}
                          type="button"
                        >
                          <Check size={15} aria-hidden="true" />
                        </button>
                      </div>
                      <button
                        className="button secondary admin-action-button"
                        disabled={Boolean(busyUser) || user.super_admin}
                        onClick={() => handleUserUpdate(
                          user,
                          { suspended: !user.suspended },
                          `${user.email} ${user.suspended ? 'restored' : 'suspended'}.`,
                        )}
                        type="button"
                      >
                        {user.suspended ? 'Restore' : 'Suspend'}
                      </button>
                      <button
                        aria-label={`Delete ${user.email}`}
                        className="admin-delete-button"
                        disabled={Boolean(busyUser) || user.super_admin}
                        onClick={() => handleDeleteUser(user)}
                        type="button"
                      >
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!users.length && (
                <tr><td className="admin-empty" colSpan="4">No matching users.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="admin-pagination">
          <button
            className="button secondary"
            disabled={page === 0 || busy}
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            type="button"
          >
            Previous
          </button>
          <span>Page {page + 1}</span>
          <button
            className="button secondary"
            disabled={(page + 1) * pageSize >= totalUsers || busy}
            onClick={() => setPage((current) => current + 1)}
            type="button"
          >
            Next
          </button>
        </div>
        <div className="admin-duration">
          <label htmlFor="admin-plan-duration">Subscription assignment duration</label>
          <input
            id="admin-plan-duration"
            max="3650"
            min="1"
            onChange={(event) => setDurationDays(event.target.value)}
            required
            type="number"
            value={durationDays}
          />
          <span>days</span>
        </div>
      </section>

      <section aria-labelledby="admin-payments-title" className="panel admin-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Manual UPI review</p>
            <h2 id="admin-payments-title">Pending payments</h2>
          </div>
          <span className="muted">{payments.length} awaiting review</span>
        </div>
        <label className="admin-review-note" htmlFor="payment-review-note">
          Optional note for the selected review
          <input
            id="payment-review-note"
            maxLength={1000}
            onChange={(event) => setReviewNote(event.target.value)}
            placeholder="Add a note"
            value={reviewNote}
          />
        </label>
        {payments.length ? (
          <div className="admin-payment-list">
            {payments.map((payment) => (
              <article className="admin-payment" key={payment.payment_id}>
                <div>
                  <strong>{payment.email}</strong>
                  <span>{payment.plan} · ₹{payment.amount_rupees}</span>
                  <small>
                    {payment.transaction_reference || 'No transaction reference'} ·{' '}
                    {new Date(payment.submitted_at).toLocaleString()}
                  </small>
                </div>
                <div className="admin-payment-actions">
                  <button
                    className="button secondary"
                    disabled={busyPayment === payment.payment_id}
                    onClick={() => handleReceipt(payment)}
                    type="button"
                  >
                    <ExternalLink size={15} aria-hidden="true" /> Receipt
                  </button>
                  <button
                    className="button primary"
                    disabled={busyPayment === payment.payment_id}
                    onClick={() => handlePaymentReview(payment, 'approved')}
                    type="button"
                  >
                    Approve
                  </button>
                  <button
                    className="button secondary"
                    disabled={busyPayment === payment.payment_id}
                    onClick={() => handlePaymentReview(payment, 'rejected')}
                    type="button"
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : <p className="muted admin-empty-copy">There are no pending payments.</p>}
      </section>

      {receipt && (
        <div className="admin-receipt-backdrop" onClick={() => setReceipt(null)} role="presentation">
          <section
            aria-labelledby="receipt-title"
            aria-modal="true"
            className="admin-receipt-dialog"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <header>
              <h2 id="receipt-title">Payment receipt #{receipt.id}</h2>
              <button aria-label="Close receipt" onClick={() => setReceipt(null)} type="button">
                <X size={18} aria-hidden="true" />
              </button>
            </header>
            {receipt.type.startsWith('image/') ? (
              <img alt={`Payment receipt ${receipt.id}`} src={receipt.url} />
            ) : (
              <a href={receipt.url} rel="noreferrer" target="_blank">Open receipt</a>
            )}
          </section>
        </div>
      )}
    </main>
  )
}
