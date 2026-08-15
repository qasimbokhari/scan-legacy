import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'

interface Record {
  id: string
  [key: string]: any
}

interface RecordTableProps {
  recordType: 'materials' | 'toxicity' | 'sensor-performance'
  onViewAuditLog?: (recordId: string) => void
}

function RecordTable({ recordType, onViewAuditLog }: RecordTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sortColumn, setSortColumn] = useState<string>('created_at')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  const { data, isLoading, error } = useQuery({
    queryKey: ['records', recordType, statusFilter],
    queryFn: () => api.get(`/records/${recordType}${statusFilter ? `?status=${statusFilter}` : ''}`).then(res => res.data)
  })

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const handleExportCSV = () => {
    if (!data?.items) return

    const headers = Object.keys(data.items[0] || {})
    const csvContent = [
      headers.join(','),
      ...data.items.map((row: Record) => 
        headers.map(header => {
          const value = row[header]
          // Handle nested objects and arrays
          if (typeof value === 'object' && value !== null) {
            return JSON.stringify(value)
          }
          return String(value || '')
        }).join(',')
      )
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${recordType}_export.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) return <div>Loading...</div>
  if (error) return <div style={{ color: 'red' }}>Error loading records</div>

  const records = data?.items || []
  const sortedRecords = [...records].sort((a, b) => {
    const aVal = a[sortColumn]
    const bVal = b[sortColumn]
    
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal)
    }
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    }
    
    return 0
  })

  const columns = records.length > 0 ? Object.keys(records[0]).filter(key => key !== '_sa_instance_state') : []

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div>
          <label style={{ marginRight: '0.5rem' }}>Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: '0.5rem', border: '1px solid #ccc' }}
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <button
          onClick={handleExportCSV}
          disabled={records.length === 0}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            cursor: records.length === 0 ? 'not-allowed' : 'pointer',
            opacity: records.length === 0 ? 0.6 : 1
          }}
        >
          Export CSV
        </button>
      </div>

      {records.length === 0 ? (
        <div>No records found</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #ddd' }}>
            <thead>
              <tr style={{ backgroundColor: '#f5f5f5' }}>
                {columns.map(column => (
                  <th
                    key={column}
                    onClick={() => handleSort(column)}
                    style={{
                      padding: '0.75rem',
                      textAlign: 'left',
                      border: '1px solid #ddd',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    {column} {sortColumn === column && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                ))}
                <th style={{ padding: '0.75rem', border: '1px solid #ddd' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedRecords.map((record, index) => (
                <tr key={record.id || index}>
                  {columns.map(column => (
                    <td key={column} style={{ padding: '0.75rem', border: '1px solid #ddd' }}>
                      {String(record[column] ?? '')}
                    </td>
                  ))}
                  <td style={{ padding: '0.75rem', border: '1px solid #ddd' }}>
                    <button
                      onClick={() => onViewAuditLog && onViewAuditLog(record.id)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        fontSize: '0.75rem',
                        backgroundColor: '#17a2b8',
                        color: 'white',
                        border: 'none',
                        cursor: 'pointer',
                        borderRadius: '3px'
                      }}
                    >
                      Audit Log
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
        Showing {records.length} of {data?.total || 0} records
      </div>
    </div>
  )
}

export default RecordTable