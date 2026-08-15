import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

function App() {
  const { accessToken, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ padding: '2rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>SCAN Legacy Frontend</h1>
        {accessToken && (
          <button onClick={handleLogout} style={{ padding: '0.5rem 1rem' }}>
            Logout
          </button>
        )}
      </header>
      <Outlet />
    </div>
  )
}

export default App
