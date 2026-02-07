import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/data/events.json')
        const data = await response.json()
        setEvents(data)
      } catch (error) {
        console.error("Failed to fetch events", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Poll every 5 seconds
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="logo">n8n // SELF_HEALER</div>
        <div className="status-indicator active">
          <span className="blink">●</span> SYSTEM ONLINE
        </div>
      </header>
      
      <main>
        <div className="kpi-grid">
          <div className="kpi-card">
            <h3>Active Errors</h3>
            <div className="value red">
              {events.filter(e => e.status === 'Detected').length}
            </div>
          </div>
          <div className="kpi-card">
            <h3>Self-Healed</h3>
            <div className="value green">
              {events.filter(e => e.status === 'Resolved').length}
            </div>
          </div>
          <div className="kpi-card">
            <h3>Success Rate</h3>
            <div className="value">
              {events.length ? Math.round((events.filter(e => e.status === 'Resolved').length / events.length) * 100) : 0}%
            </div>
          </div>
        </div>

        <div className="events-list">
          <h2>Event Log</h2>
          {loading ? (
            <div className="loading">Initializing Neural Link...</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Workflow</th>
                  <th>Error</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id} className={`status-${event.status.toLowerCase()}`}>
                    <td>{new Date(event.timestamp).toLocaleTimeString()}</td>
                    <td>{event.workflowName}</td>
                    <td className="error-msg">{event.error}</td>
                    <td>
                      <span className={`badge ${event.status.toLowerCase()}`}>
                        {event.status}
                      </span>
                    </td>
                    <td>
                      {event.status === 'Resolved' && <span className="action-text">Refactored</span>}
                      {event.status === 'Detected' && <span className="action-text blink">Analyzing...</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
