import { useEffect, useState } from 'react'
import './App.css'
import DevOps from './DevOps'

function App() {
  const [activeNav, setActiveNav] = useState('Dashboard')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [fixedAnswer, setFixedAnswer] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [notes, setNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(null)
  const [selectedNote, setSelectedNote] = useState(null)

  const askLumora = async (
    questionText = question,
    documentId = selectedNote?.document_id
    ) => {
    const trimmedQuestion = questionText.trim()

    if (!trimmedQuestion || loading) {
      return
    }

    setQuestion(trimmedQuestion)
    setLoading(true)
    setError('')
    setAnswer(null)
    setFixedAnswer(null)

    try {
      const requestBody = {
        question: trimmedQuestion,
        top_k: 5,
        ...(documentId ? { document_id: documentId } : {}),
      }

      const agenticResponse = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!agenticResponse.ok) {
        throw new Error(`Agentic RAG request failed with status ${agenticResponse.status}`)
      }

      const agenticData = await agenticResponse.json()
      setAnswer(agenticData)

      const fixedResponse = await fetch('/api/v1/ask/fixed', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!fixedResponse.ok) {
        throw new Error(`Fixed RAG request failed with status ${fixedResponse.status}`)
      }

      const fixedData = await fixedResponse.json()
      setFixedAnswer(fixedData)
    } catch (err) {
      console.error(err)
      setError('Unable to get an answer from Lumora. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleQuestionSubmit = (event) => {
    event.preventDefault()
    askLumora()
  }

  const handleSuggestion = (suggestion) => {
    askLumora(suggestion)
  }

  const loadNotes = async () => {
    setNotesLoading(true)

    try {
      const response = await fetch('/api/v1/documents')

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }

      const data = await response.json()
      setNotes(data)
    } catch (err) {
      console.error(err)
    } finally {
      setNotesLoading(false)
    }
  }

  useEffect(() => {
    if (activeNav === 'My Notes') {
      loadNotes()
    }
  }, [activeNav])

  const handleFileUpload = async () => {
    if (!selectedFile || uploading) {
      return
    }

    setUploading(true)
    setUploadMessage('')
    setUploadError('')

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed')
      }

      setUploadMessage(
        `${data.file_name} uploaded successfully and processed into ${data.chunk_count} chunk${data.chunk_count === 1 ? '' : 's'}.`
      )
      setSelectedFile(null)
      await loadNotes()
    } catch (err) {
      console.error(err)
      setUploadError(err.message || 'Unable to upload the note. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const courses = [
    {
      title: 'Machine Learning',
      description: 'Learn supervised, unsupervised and reinforcement learning.',
      progress: 68,
      lessons: '12 of 18 lessons',
      icon: 'ML',
    },
    {
      title: 'Database Systems',
      description: 'Understand relational databases, SQL and data management.',
      progress: 42,
      lessons: '7 of 16 lessons',
      icon: 'DB',
    },
    {
      title: 'Artificial Intelligence',
      description: 'Explore intelligent systems, agents and modern AI.',
      progress: 24,
      lessons: '4 of 17 lessons',
      icon: 'AI',
    },
  ]

  const navItems = [
    { name: 'Dashboard', icon: '⌂' },
    { name: 'My Courses', icon: '▣' },
    { name: 'My Notes', icon: '▤' },
    { name: 'Ask Lumora', icon: '✦' },
    { name: 'Quiz', icon: '✓' },
    { name: 'Progress', icon: '◔' },
    { name: 'Observability', icon: '◉' },
  ]

  const deleteNote = async (documentId) => {
    if (deleteLoading !== null) {
      return
    }

    const confirmed = window.confirm(
      'Are you sure you want to delete this note? Its stored content and searchable chunks will also be removed.'
    )

    if (!confirmed) {
      return
    }

    setDeleteLoading(documentId)
    setUploadError('')
    setUploadMessage('')

    try {
      const response = await fetch(`/api/v1/documents/${documentId}`, {
        method: 'DELETE',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to delete note')
      }

      setNotes((currentNotes) =>
        currentNotes.filter((note) => note.document_id !== documentId)
      )
    } catch (err) {
      console.error(err)
      setUploadError(err.message || 'Unable to delete the note.')
    } finally {
      setDeleteLoading(null)
    }
  }

  const renderMyNotes = () => (
    <section className="notes-page">
      <div className="section-header">
        <div>
          <p className="eyebrow">PERSONAL LEARNING</p>
          <h2>My Notes</h2>
          <p>Upload your study materials and use them with Lumora.</p>
        </div>
      </div>

      <div className="notes-upload-card">
        <div className="upload-icon">▤</div>

        <h3>Upload a study note</h3>
        <p>
          Add PDF, DOCX, or TXT files. Lumora will extract the content,
          create searchable chunks, and add them to your personal knowledge base.
        </p>

        <label className="file-picker">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] || null)
              setUploadMessage('')
              setUploadError('')
            }}
            disabled={uploading}
          />
          <span>
            {selectedFile ? selectedFile.name : 'Choose a file'}
          </span>
        </label>

        {selectedFile && (
          <button
            type="button"
            className="upload-button"
            onClick={handleFileUpload}
            disabled={uploading}
          >
            {uploading ? 'Uploading and processing...' : 'Upload Note →'}
          </button>
        )}

        {uploadMessage && (
          <div className="upload-status success">
            <strong>✓ Upload complete</strong>
            <span>{uploadMessage}</span>
          </div>
        )}

        {uploadError && (
          <div className="upload-status failure">
            <strong>⚠ Action failed</strong>
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      <div className="notes-list-section">
        <div className="section-header">
          <div>
            <h2>Your Notes</h2>
            <p>Materials currently available to Lumora.</p>
          </div>
          <span className="notes-count">
            {notes.length} {notes.length === 1 ? 'note' : 'notes'}
          </span>
        </div>

        {notesLoading ? (
          <div className="notes-empty">
            <strong>Loading your notes...</strong>
            <span>Fetching your uploaded learning materials.</span>
          </div>
        ) : notes.length === 0 ? (
          <div className="notes-empty">
            <strong>No notes uploaded yet</strong>
            <span>Upload your first study material above.</span>
          </div>
        ) : (
          <div className="notes-list">
            {notes.map((note) => (
              <article className="note-card" key={note.document_id}>
                <div className="note-file-icon">
                  {note.document_type.toUpperCase()}
                </div>

                <div className="note-details">
                  <h3>{note.file_name}</h3>
                  <div className="note-meta">
                    <span>{note.document_type.toUpperCase()}</span>
                    <span>{note.chunk_count} chunks</span>
                    <span>
                      {note.created_at
                        ? new Date(note.created_at).toLocaleDateString()
                        : 'Unknown date'}
                    </span>
                  </div>
                  <span className="note-visibility">
                    Private · Personal knowledge base
                  </span>
                </div>

                <div className="note-actions">
                  <button
                    type="button"
                    className="ask-note-button"
                    onClick={() => {
                      setSelectedNote(note)
                      setQuestion('')
                      setAnswer(null)
                      setError('')
                      setActiveNav('Ask Lumora')
                    }}
                  >
                    Ask about this note
                  </button>

                  <button
                    type="button"
                    className="delete-note-button"
                    onClick={() => deleteNote(note.document_id)}
                    disabled={deleteLoading !== null}
                  >
                    {deleteLoading === note.document_id
                      ? 'Deleting...'
                      : 'Delete'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )



  return (
    <div className="lumora-app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">L</div>
          <div>
            <div className="brand-name">Lumora</div>
            <div className="brand-tagline">Learn smarter</div>
          </div>
        </div>

        <nav className="navigation">
          <div className="nav-label">LEARNING</div>

          {navItems.map((item) => (
            <button
              key={item.name}
              className={`nav-item ${activeNav === item.name ? 'active' : ''}`}
              onClick={() => setActiveNav(item.name)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.name}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>

          <div className="user-mini">
            <div className="avatar">S</div>
            <div className="user-details">
              <strong>Student</strong>
              <span>Learning account</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activeNav === 'Observability' ? (
          <DevOps />
        ) : activeNav === 'My Notes' ? (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">PERSONAL LEARNING</p>
                <h1>My Notes</h1>
                <p className="welcome-text">
                  Upload and manage your personal study materials.
                </p>
              </div>

              <div className="topbar-actions">
                <button className="icon-button" aria-label="Notifications">
                  ♢
                </button>
                <div className="profile-avatar">S</div>
              </div>
            </header>

            {renderMyNotes()}
          </>
        ) : (
          <>
        <header className="topbar">
          <div>
            <p className="eyebrow">STUDENT DASHBOARD</p>
            <h1>
              {(() => {
                const hour = new Date().getHours();

                if (hour >= 5 && hour < 12) {
                  return "Good morning, Student";
                }

                if (hour >= 12 && hour < 17) {
                  return "Good afternoon, Student";
                }

                if (hour >= 17 && hour < 21) {
                  return "Good evening, Student";
                }

                return "Good night, Student";
              })()}
            </h1>
            <p className="welcome-text">
              Continue your learning journey and explore something new today.
            </p>
          </div>

          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications">
              ♢
            </button>
            <div className="profile-avatar">S</div>
          </div>
        </header>

        <section className="ask-card">
          <div className="ask-content">
            <span className="ai-badge">✦ AI LEARNING ASSISTANT</span>
            <h2>Ask Lumora</h2>
            <p>
              Ask questions about your course materials, notes, or anything
              you're learning.
            </p>

            {selectedNote && (
              <div className="selected-note-banner">
                <div>
                  <span className="selected-note-label">ASKING ABOUT</span>
                  <strong>{selectedNote.file_name}</strong>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedNote(null)}
                  disabled={loading}
                >
                  Clear
                </button>
              </div>
            )}

            <form className="question-box" onSubmit={handleQuestionSubmit}>
              <input
                type="text"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What would you like to learn today?"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !question.trim()}
              >
                {loading ? 'Thinking...' : 'Ask Lumora'}
                <span>→</span>
              </button>
            </form>

            <div className="suggestions">
              <button
                type="button"
                onClick={() => handleSuggestion('Explain supervised learning')}
                disabled={loading}
              >
                Explain supervised learning
              </button>
              <button
                type="button"
                onClick={() => handleSuggestion('Help me understand neural networks')}
                disabled={loading}
              >
                Help me understand neural networks
              </button>
              <button
                type="button"
                onClick={() => handleSuggestion('Quiz me on databases')}
                disabled={loading}
              >
                Quiz me on databases
              </button>
            </div>

            {loading && (
              <div className="answer-panel loading-panel">
                <div className="answer-header">
                  <span className="answer-label">✦ LUMORA IS THINKING</span>
                </div>
                <p>Searching your learning materials and preparing an answer...</p>
              </div>
            )}

            {error && (
              <div className="answer-panel error-panel">
                <div className="answer-header">
                  <span className="answer-label">⚠ ERROR</span>
                </div>
                <p>{error}</p>
              </div>
            )}

            {answer && !loading && (
              <>
                <div className="answer-panel">
                  <div className="answer-header">
                    <span className="answer-label">✦ LUMORA ANSWER</span>
                    <span className="strategy-badge">
                      {answer.final_strategy || answer.selected_strategy}
                    </span>
                  </div>

                  <div className="answer-question">
                    {answer.question}
                  </div>

                  <div className="answer-text">
                    {answer.answer}
                  </div>

                  <div className="answer-metadata">
                    <div>
                      <span>Retrieval</span>
                      <strong>{answer.final_strategy || answer.selected_strategy}</strong>
                    </div>

                    <div>
                      <span>Sources</span>
                      <strong>{answer.sources?.length || 0}</strong>
                    </div>

                    <div>
                      <span>Context</span>
                      <strong>
                        {answer.context_sufficient ? 'Sufficient' : 'Insufficient'}
                      </strong>
                    </div>

                    <div>
                      <span>Context chunks</span>
                      <strong>{answer.selected_context_count ?? '-'}</strong>
                    </div>

                    <div>
                      <span>Fallbacks</span>
                      <strong>{answer.fallback_count ?? 0}</strong>
                    </div>

                    <div>
                      <span>Prompt tokens</span>
                      <strong>{answer.prompt_tokens ?? '-'}</strong>
                    </div>

                    <div>
                      <span>Completion tokens</span>
                      <strong>{answer.completion_tokens ?? '-'}</strong>
                    </div>

                    <div>
                      <span>Total tokens</span>
                      <strong>{answer.total_tokens ?? '-'}</strong>
                    </div>

                    <div>
                      <span>Retrieval time</span>
                      <strong>
                        {answer.latency?.retrieval_seconds != null
                          ? `${answer.latency.retrieval_seconds.toFixed(1)}s`
                          : '-'}
                      </strong>
                    </div>

                    <div>
                      <span>Generation time</span>
                      <strong>
                        {answer.latency?.generation_seconds != null
                          ? `${answer.latency.generation_seconds.toFixed(1)}s`
                          : '-'}
                      </strong>
                    </div>

                    <div>
                      <span>Total time</span>
                      <strong>
                        {answer.latency?.total_seconds != null
                          ? `${answer.latency.total_seconds.toFixed(1)}s`
                          : '-'}
                      </strong>
                    </div>
                  </div>

                  {answer.sources?.length > 0 && (
                    <div className="answer-sources">
                      <span className="sources-title">Sources used</span>

                      {answer.sources.map((source) => (
                        <div
                          className="source-item"
                          key={`${source.document_id}-${source.chunk_id}`}
                        >
                          <span>
                            Document {source.document_id} · Chunk {source.chunk_id}
                          </span>
                          <span>
                            {source.retrieval_method} · {source.score.toFixed(3)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {fixedAnswer && (
                  <div className="rag-comparison">
                    <div className="comparison-header">
                      <span>AGENTIC RAG vs FIXED RAG</span>
                      <small>Same question, two retrieval approaches</small>
                    </div>

                    <div className="comparison-grid">
                      <div className="comparison-card">
                        <div className="comparison-card-header">
                          <strong>Agentic RAG</strong>
                          <span>
                            {answer.final_strategy || answer.selected_strategy}
                          </span>
                        </div>

                        <div className="comparison-metrics">
                          <div>
                            <span>Context chunks</span>
                            <strong>{answer.selected_context_count ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Prompt tokens</span>
                            <strong>{answer.prompt_tokens ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Total tokens</span>
                            <strong>{answer.total_tokens ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Total time</span>
                            <strong>
                              {answer.latency?.total_seconds != null
                                ? `${answer.latency.total_seconds.toFixed(1)}s`
                                : '-'}
                            </strong>
                          </div>
                        </div>
                      </div>

                      <div className="comparison-card">
                        <div className="comparison-card-header">
                          <strong>Fixed RAG</strong>
                          <span>{fixedAnswer.retrieval_method}</span>
                        </div>

                        <div className="comparison-metrics">
                          <div>
                            <span>Context chunks</span>
                            <strong>{fixedAnswer.selected_context_count ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Prompt tokens</span>
                            <strong>{fixedAnswer.prompt_tokens ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Total tokens</span>
                            <strong>{fixedAnswer.total_tokens ?? '-'}</strong>
                          </div>

                          <div>
                            <span>Total time</span>
                            <strong>
                              {fixedAnswer.latency?.total_seconds != null
                                ? `${fixedAnswer.latency.total_seconds.toFixed(1)}s`
                                : '-'}
                            </strong>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            </div>
          <div className="ask-visual">
            <div className="orb">
              <span>✦</span>
            </div>
            <div className="floating-card card-one">
              <span>AI</span>
              Personalized
            </div>
            <div className="floating-card card-two">
              <span>RAG</span>
              Course-aware
            </div>
          </div>
        </section>

        <section className="section-header">
          <div>
            <h2>Continue Learning</h2>
            <p>Pick up where you left off.</p>
          </div>
          <button className="text-button">View all →</button>
        </section>

        <section className="course-grid">
          {courses.map((course) => (
            <article className="course-card" key={course.title}>
              <div className="course-top">
                <div className="course-icon">{course.icon}</div>
                <button className="more-button">•••</button>
              </div>

              <h3>{course.title}</h3>
              <p>{course.description}</p>

              <div className="progress-info">
                <span>{course.lessons}</span>
                <strong>{course.progress}%</strong>
              </div>

              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${course.progress}%` }}
                />
              </div>

              <button className="continue-button">
                Continue learning <span>→</span>
              </button>
            </article>
          ))}
        </section>

        <section className="bottom-grid">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Recent Activity</h2>
                <p>Your latest learning activity.</p>
              </div>
              <button className="text-button">View all</button>
            </div>

            <div className="activity-list">
              <div className="activity">
                <div className="activity-icon">✦</div>
                <div>
                  <strong>Asked Lumora about supervised learning</strong>
                  <span>Machine Learning · 20 minutes ago</span>
                </div>
              </div>

              <div className="activity">
                <div className="activity-icon">✓</div>
                <div>
                  <strong>Completed Neural Networks quiz</strong>
                  <span>Machine Learning · Yesterday</span>
                </div>
              </div>

              <div className="activity">
                <div className="activity-icon">▤</div>
                <div>
                  <strong>Added new study notes</strong>
                  <span>Database Systems · 2 days ago</span>
                </div>
              </div>
            </div>
          </div>

          <div className="panel goals-panel">
            <div className="panel-header">
              <div>
                <h2>Today's Goal</h2>
                <p>Keep your learning streak going.</p>
              </div>
              <span className="goal-icon">✦</span>
            </div>

            <div className="goal-progress">
              <div className="goal-ring">
                <strong>72%</strong>
              </div>
              <div>
                <strong>36 / 50 minutes</strong>
                <span>Learning time today</span>
              </div>
            </div>

            <div className="goal-message">
              <strong>You're doing great!</strong>
              <span>14 more minutes to complete today's goal.</span>
            </div>
          </div>
        </section>

        <footer className="footer">
          <span>© 2026 Lumora</span>
          <span>AI-powered personalized learning</span>
        </footer>
          </>
        )}
      </main>
    </div>
  )
}

export default App
