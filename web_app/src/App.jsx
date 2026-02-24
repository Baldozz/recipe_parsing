import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './index.css' // Import global styles

function App() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResult('')

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/menu'
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate menu. Is the backend running?')
      }

      // Check content type to see if it's JSON (error inside API) or stream
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        if (data.error !== false) {
          setError(data.content || 'An error occurred server-side.');
          setLoading(false);
          return;
        }
        setResult(data.content);
        setLoading(false);
        return;
      }

      // Handle streaming response
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let done = false
      let fullText = ""
      while (!done) {
        const { value, done: readerDone } = await reader.read()
        done = readerDone
        if (value) {
          const chunk = decoder.decode(value, { stream: true })
          fullText += chunk
          setResult(fullText)
        }
      }
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header>
        <h1>Ludo's Menu Builder</h1>
      </header>
      <main className="container">
        <form className="input-section" onSubmit={handleSubmit}>
          <textarea
            placeholder="E.g., Create a 4-course menu for a Gala at the White House..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? 'Sourcing Ideas...' : 'Generate Menus'}
          </button>
        </form>

        {error && (
          <div className="result-section" style={{ borderColor: '#f85149' }}>
            <h2>Error</h2>
            <p style={{ color: '#f85149' }}>{error}</p>
          </div>
        )}

        {(loading || result) && !error && (
          <div className="result-section">
            <h2>Proposed Menus</h2>
            {loading && !result && (
              <div className="loading">
                <div className="loading-spinner" />
                <span>Searching your recipe database and reasoning over past combinations...</span>
              </div>
            )}
            {result && (
              <div className="content">
                <ReactMarkdown>{result}</ReactMarkdown>
              </div>
            )}
            {loading && result && (
              <div className="loading" style={{ marginTop: '1rem' }}>
                <div className="loading-spinner" />
                <span>Refining...</span>
              </div>
            )}
          </div>
        )}
      </main>
    </>
  )
}

export default App
