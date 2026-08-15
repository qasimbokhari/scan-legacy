import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import MaterialRecordForm from '../components/MaterialRecordForm'
import ToxicityRecordForm from '../components/ToxicityRecordForm'
import SensorPerformanceRecordForm from '../components/SensorPerformanceRecordForm'
import RecordTable from '../components/RecordTable'
import AuditLogView from '../components/AuditLogView'
import DataHealthPanel from '../components/DataHealthPanel'

type View = 'overview' | 'materials' | 'toxicity' | 'sensor-performance' | 'audit-log'

function Dashboard() {
  const { user } = useAuth()
  const [currentView, setCurrentView] = useState<View>('overview')
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const { data, error, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then(res => res.data),
  })

  const handleFormSuccess = () => {
    setShowForm(false)
    // Refresh queries would happen here with TanStack Query's invalidate
  }

  const handleViewAuditLog = (recordId: string) => {
    setSelectedRecordId(recordId)
    setCurrentView('audit-log')
  }

  return (
    <div>
      <h2>Dashboard</h2>
      {user && <p>Welcome, {user.email}</p>}
      
      <div style={{ marginTop: '2rem' }}>
        <h3>Backend Status</h3>
        {isLoading && <p>Checking backend status...</p>}
        {error && <p style={{ color: 'red' }}>Backend status: error</p>}
        {data && data.status === 'ok' && <p style={{ color: 'green' }}>Backend status: ok</p>}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <nav style={{ marginBottom: '1rem', borderBottom: '1px solid #ddd', paddingBottom: '0.5rem' }}>
          <button
            onClick={() => setCurrentView('overview')}
            style={{ 
              padding: '0.5rem 1rem', 
              marginRight: '0.5rem',
              backgroundColor: currentView === 'overview' ? '#007bff' : '#f8f9fa',
              color: currentView === 'overview' ? 'white' : 'black',
              border: '1px solid #ddd',
              cursor: 'pointer'
            }}
          >
            Overview
          </button>
          <button
            onClick={() => setCurrentView('materials')}
            style={{ 
              padding: '0.5rem 1rem', 
              marginRight: '0.5rem',
              backgroundColor: currentView === 'materials' ? '#007bff' : '#f8f9fa',
              color: currentView === 'materials' ? 'white' : 'black',
              border: '1px solid #ddd',
              cursor: 'pointer'
            }}
          >
            Materials
          </button>
          <button
            onClick={() => setCurrentView('toxicity')}
            style={{ 
              padding: '0.5rem 1rem', 
              marginRight: '0.5rem',
              backgroundColor: currentView === 'toxicity' ? '#007bff' : '#f8f9fa',
              color: currentView === 'toxicity' ? 'white' : 'black',
              border: '1px solid #ddd',
              cursor: 'pointer'
            }}
          >
            Toxicity
          </button>
          <button
            onClick={() => setCurrentView('sensor-performance')}
            style={{ 
              padding: '0.5rem 1rem', 
              backgroundColor: currentView === 'sensor-performance' ? '#007bff' : '#f8f9fa',
              color: currentView === 'sensor-performance' ? 'white' : 'black',
              border: '1px solid #ddd',
              cursor: 'pointer'
            }}
          >
            Sensor Performance
          </button>
        </nav>

        {currentView === 'overview' && (
          <div>
            <DataHealthPanel />
          </div>
        )}

        {currentView === 'materials' && (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <button
                onClick={() => setShowForm(!showForm)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {showForm ? 'Cancel' : 'Add New Material Record'}
              </button>
            </div>

            {showForm && (
              <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
                <h3>New Material Record</h3>
                <MaterialRecordForm onSuccess={handleFormSuccess} />
              </div>
            )}

            <RecordTable recordType="materials" onViewAuditLog={handleViewAuditLog} />
          </div>
        )}

        {currentView === 'toxicity' && (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <button
                onClick={() => setShowForm(!showForm)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {showForm ? 'Cancel' : 'Add New Toxicity Record'}
              </button>
            </div>

            {showForm && (
              <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
                <h3>New Toxicity Record</h3>
                <ToxicityRecordForm onSuccess={handleFormSuccess} />
              </div>
            )}

            <RecordTable recordType="toxicity" onViewAuditLog={handleViewAuditLog} />
          </div>
        )}

        {currentView === 'sensor-performance' && (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <button
                onClick={() => setShowForm(!showForm)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {showForm ? 'Cancel' : 'Add New Sensor Performance Record'}
              </button>
            </div>

            {showForm && (
              <div style={{ marginBottom: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '4px' }}>
                <h3>New Sensor Performance Record</h3>
                <SensorPerformanceRecordForm onSuccess={handleFormSuccess} />
              </div>
            )}

            <RecordTable recordType="sensor-performance" onViewAuditLog={handleViewAuditLog} />
          </div>
        )}

        {currentView === 'audit-log' && selectedRecordId && (
          <div>
            <button
              onClick={() => setCurrentView('materials')}
              style={{
                padding: '0.5rem 1rem',
                marginBottom: '1rem',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              Back to Materials
            </button>
            <AuditLogView recordType="material_record" recordId={selectedRecordId} />
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
