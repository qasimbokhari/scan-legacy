import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from './App'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'

// Protected route wrapper component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuth()
  
  if (!accessToken) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

// Public route wrapper component
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuth()
  
  if (accessToken) {
    return <Navigate to="/" replace />
  }
  
  return <>{children}</>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <AuthProvider>
        <App />
      </AuthProvider>
    ),
    children: [
      {
        index: true,
        element: (
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'login',
        element: (
          <PublicRoute>
            <Login />
          </PublicRoute>
        ),
      },
      {
        path: 'register',
        element: (
          <PublicRoute>
            <Register />
          </PublicRoute>
        ),
      },
    ],
  },
])
