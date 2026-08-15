import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

interface DataHealthSummary {
  material_records: number
  toxicity_records: number
  sensor_performance_records: number
  pending_reviews: number
  approved_records: number
  rejected_records: number
}

function DataHealthPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['data-health'],
    queryFn: () => api.get('/records/health/summary').then(res => res.data)
  })

  if (isLoading) return <div>Loading data health summary...</div>
  if (error) return <div style={{ color: 'red' }}>Error loading data health</div>

  const summary: DataHealthSummary = data || {
    material_records: 0,
    toxicity_records: 0,
    sensor_performance_records: 0,
    pending_reviews: 0,
    approved_records: 0,
    rejected_records: 0
  }

  return (
    <div>
      <h3>Data Health Summary</h3>
      <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Material Records</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#007bff' }}>{summary.material_records}</div>
        </div>

        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Toxicity Records</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#28a745' }}>{summary.toxicity_records}</div>
        </div>

        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f9f9f9' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Sensor Performance Records</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#17a2b8' }}>{summary.sensor_performance_records}</div>
        </div>

        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#fff3cd' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Pending Reviews</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ffc107' }}>{summary.pending_reviews}</div>
        </div>

        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#d4edda' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Approved Records</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#28a745' }}>{summary.approved_records}</div>
        </div>

        <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: '4px', backgroundColor: '#f8d7da' }}>
          <div style={{ fontSize: '0.875rem', color: '#666' }}>Rejected Records</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc3545' }}>{summary.rejected_records}</div>
        </div>
      </div>
    </div>
  )
}

export default DataHealthPanel