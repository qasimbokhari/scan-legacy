import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

function Dashboard() {
  const { user } = useAuth()
  const { data, error, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then(res => res.data),
  })

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
    </div>
  )
}

export default Dashboard
