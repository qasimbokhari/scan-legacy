import { useState } from 'react'
import api from '../lib/api'

interface ReviewActionsProps {
  recordType: 'material_record' | 'toxicity_record' | 'sensor_performance_record'
  recordId: string
  currentStatus: string
  onReviewComplete?: () => void
}

function ReviewActions({ recordType, recordId, currentStatus, onReviewComplete }: ReviewActionsProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [notes, setNotes] = useState('')

  const handleReview = async (status: 'approved' | 'rejected') => {
    setIsSubmitting(true)
    try {
      await api.put(`/records/reviews/${recordType}/${recordId}`, {
        status,
        notes: notes || undefined
      })
      if (onReviewComplete) onReviewComplete()
    } catch (error) {
      console.error('Review failed:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (currentStatus === 'approved' || currentStatus === 'rejected') {
    return (
      <div style={{ padding: '0.5rem', fontSize: '0.875rem' }}>
        <strong>Status:</strong> {currentStatus}
      </div>
    )
  }

  return (
    <div style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}>
      <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem' }}>
        <strong>Status:</strong> {currentStatus}
      </div>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Review notes (optional)"
        style={{
          width: '100%',
          padding: '0.5rem',
          marginBottom: '0.5rem',
          border: '1px solid #ccc',
          borderRadius: '4px',
          minHeight: '60px'
        }}
      />
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button
          onClick={() => handleReview('approved')}
          disabled={isSubmitting}
          style={{
            flex: 1,
            padding: '0.5rem',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            opacity: isSubmitting ? 0.6 : 1
          }}
        >
          {isSubmitting ? 'Processing...' : 'Approve'}
        </button>
        <button
          onClick={() => handleReview('rejected')}
          disabled={isSubmitting}
          style={{
            flex: 1,
            padding: '0.5rem',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            opacity: isSubmitting ? 0.6 : 1
          }}
        >
          {isSubmitting ? 'Processing...' : 'Reject'}
        </button>
      </div>
    </div>
  )
}

export default ReviewActions