import { useQuery } from '@tanstack/react-query'
import api from './lib/api'

function App() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then(res => res.data),
  })

  return (
    <div style={{ padding: '2rem' }}>
      <h1>SCAN Legacy Frontend</h1>
      {isLoading && <p>Checking backend status...</p>}
      {error && <p style={{ color: 'red' }}>Backend status: error</p>}
      {data && data.status === 'ok' && <p style={{ color: 'green' }}>Backend status: ok</p>}
    </div>
  )
}

export default App
