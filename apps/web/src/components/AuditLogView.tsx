import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

interface AuditLogViewProps {
  recordType: 'material_record' | 'toxicity_record' | 'sensor_performance_record'
  recordId: string
}

interface RecordVersion {
  id: string
  version_number: number
  data_snapshot: Record<string, any>
  edited_by: string | null
  created_at: string
}

function AuditLogView({ recordType, recordId }: AuditLogViewProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['record-versions', recordType, recordId],
    queryFn: () => api.get(`/records/${recordType}/${recordId}/versions`).then(res => res.data)
  })

  if (isLoading) return <div>Loading version history...</div>
  if (error) return <div style={{ color: 'red' }}>Error loading version history</div>

  const versions = data || []

  if (versions.length === 0) {
    return <div>No version history available</div>
  }

  return (
    <div>
      <h3>Version History</h3>
      <div style={{ marginTop: '1rem' }}>
        {versions.map((version: RecordVersion) => (
          <div
            key={version.id}
            style={{
              padding: '1rem',
              marginBottom: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#f9f9f9'
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
              Version {version.version_number} - {new Date(version.created_at).toLocaleString()}
            </div>
            <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>
              Edited by: {version.edited_by || 'Unknown'}
            </div>
            <div>
              <strong>Data Snapshot:</strong>
              <pre style={{
                backgroundColor: '#fff',
                padding: '0.5rem',
                marginTop: '0.5rem',
                fontSize: '0.75rem',
                overflowX: 'auto',
                border: '1px solid #eee'
              }}>
                {JSON.stringify(version.data_snapshot, null, 2)}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default AuditLogView