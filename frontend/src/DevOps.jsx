import { useCallback, useEffect, useMemo, useState } from 'react'
import './DevOps.css'

const targets = [
  { id: 'healthy', label: 'Healthy test container' },
  { id: 'failing', label: 'Failing test container' },
]

async function fetchJson(url) {
  const response = await fetch(url)
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`)
  }
  return data
}

function Metric({ label, value }) {
  return (
    <div className="observability-resource-item">
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
    </div>
  )
}

function DevOps() {
  const [inventory, setInventory] = useState(null)
  const [inventoryLoading, setInventoryLoading] = useState(false)
  const [inventoryError, setInventoryError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedId, setSelectedId] = useState('')
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [assessmentResults, setAssessmentResults] = useState({})
  const [assessmentLoading, setAssessmentLoading] = useState({})
  const [assessmentErrors, setAssessmentErrors] = useState({})
  const [results, setResults] = useState({})
  const [diagnosisLoading, setDiagnosisLoading] = useState({})
  const [diagnosisErrors, setDiagnosisErrors] = useState({})

  const loadInventory = useCallback(async () => {
    setInventoryLoading(true)
    setInventoryError('')
    try {
      const data = await fetchJson('/api/v1/devops/containers')
      setInventory(data)
      setSelectedId((current) => {
        if (current && data.containers?.some((c) => c.id === current)) {
          return current
        }
        return data.containers?.[0]?.id || ''
      })
    } catch (error) {
      setInventoryError(error.message || 'Unable to load container inventory.')
    } finally {
      setInventoryLoading(false)
    }
  }, [])

  const loadDetail = useCallback(async (containerId) => {
    if (!containerId) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setDetailError('')
    try {
      const data = await fetchJson(
        `/api/v1/devops/containers/${encodeURIComponent(containerId)}`
      )
      setDetail(data)
    } catch (error) {
      setDetail(null)
      setDetailError(error.message || 'Unable to load container evidence.')
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const assessContainer = useCallback(async (containerId) => {
    if (!containerId) return

    setAssessmentLoading((current) => ({ ...current, [containerId]: true }))
    setAssessmentErrors((current) => ({ ...current, [containerId]: '' }))

    try {
      const data = await fetchJson(
        `/api/v1/devops/containers/${encodeURIComponent(containerId)}/assessment`
      )
      setAssessmentResults((current) => ({
        ...current,
        [containerId]: data,
      }))
    } catch (error) {
      setAssessmentErrors((current) => ({
        ...current,
        [containerId]: error.message || 'Unable to assess this container.',
      }))
    } finally {
      setAssessmentLoading((current) => ({
        ...current,
        [containerId]: false,
      }))
    }
  }, [])

  const diagnose = useCallback(async (target) => {
    setDiagnosisLoading((current) => ({ ...current, [target]: true }))
    setDiagnosisErrors((current) => ({ ...current, [target]: '' }))
    try {
      const data = await fetchJson(
        `/api/v1/devops/diagnose?target=${encodeURIComponent(target)}`
      )
      setResults((current) => ({ ...current, [target]: data }))
    } catch (error) {
      setDiagnosisErrors((current) => ({
        ...current,
        [target]: error.message || 'Unable to retrieve diagnostic results.',
      }))
    } finally {
      setDiagnosisLoading((current) => ({ ...current, [target]: false }))
    }
  }, [])

  useEffect(() => {
    loadInventory()
    targets.forEach(({ id }) => diagnose(id))
  }, [loadInventory, diagnose])

  useEffect(() => {
    loadDetail(selectedId)
  }, [selectedId, loadDetail])

  const filteredContainers = useMemo(() => {
    const containers = inventory?.containers || []
    const query = search.trim().toLowerCase()
    return containers.filter((container) => {
      const matchesStatus =
        statusFilter === 'all' || container.status === statusFilter
      const searchable = [
        container.container,
        container.image,
        container.id,
        container.short_id,
      ].filter(Boolean).join(' ').toLowerCase()
      return matchesStatus && (!query || searchable.includes(query))
    })
  }, [inventory, search, statusFilter])

  const selectedSummary = inventory?.containers?.find(
    (container) => container.id === selectedId
  )
  const metrics = detail?.metrics
  const selectedAssessment = assessmentResults[selectedId]?.assessment
  const isAssessingSelected = Boolean(assessmentLoading[selectedId])
  const selectedAssessmentError = assessmentErrors[selectedId]
  const analysis = (target) => results[target]?.analysis

  return (
    <section className="observability-page">
      <header className="observability-header">
        <div>
          <p className="eyebrow">LUMORA OPERATIONS</p>
          <h1>Observability &amp; Diagnostics</h1>
          <p className="welcome-text">
            Discover containers and investigate infrastructure issues using collected evidence.
          </p>
        </div>
        <button
          className="observability-refresh"
          onClick={loadInventory}
          disabled={inventoryLoading}
        >
          {inventoryLoading ? 'Refreshing…' : 'Refresh inventory'}
        </button>
      </header>

      <div className="observability-notice">
        <strong>Read-only diagnostics</strong>
        <span>
          Container details, metrics and logs come from the latest saved snapshot.
          Resource values are not live measurements. Diagnoses are evidence-based
          and should be verified before taking operational action.
        </span>
      </div>

      <section className="observability-analysis">
        <h2>Container inventory</h2>
        <div className="inventory-summary">
          <Metric label="Discovered" value={inventory?.total_discovered ?? '—'} />
          <Metric label="Collected" value={inventory?.total_collected ?? '—'} />
          <Metric label="Collection failures" value={inventory?.total_failed ?? '—'} />
          <Metric
            label="Snapshot"
            value={inventory?.collected_at
              ? new Date(inventory.collected_at).toLocaleString()
              : '—'}
          />
        </div>
      </section>

      {inventoryError && (
        <div className="observability-error">{inventoryError}</div>
      )}

      <div className="inventory-controls">
        <input
          type="search"
          aria-label="Search containers"
          placeholder="Search by container, image or ID…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filter by container status"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="running">Running</option>
          <option value="exited">Exited</option>
        </select>
      </div>

      <div className="inventory-layout">
        <section className="inventory-list" aria-label="Discovered containers">
          <div className="inventory-list-heading">
            <h3>Discovered containers</h3>
            <span>{filteredContainers.length} shown</span>
          </div>

          {inventoryLoading && !inventory && (
            <p className="observability-muted">Loading inventory…</p>
          )}

          {!inventoryLoading && !inventoryError && filteredContainers.length === 0 && (
            <p className="observability-muted">No containers match this filter.</p>
          )}

          {filteredContainers.map((container) => (
            <button
              type="button"
              className={`inventory-row ${selectedId === container.id ? 'inventory-row-selected' : ''}`}
              key={container.id}
              onClick={() => setSelectedId(container.id)}
            >
              <span className={`inventory-dot ${container.status === 'running' ? 'dot-running' : 'dot-stopped'}`} />
              <span className="inventory-row-main">
                <strong>{container.container || container.short_id}</strong>
                <small>{container.image || 'Image unavailable'}</small>
                <small>{container.short_id || container.id}</small>
              </span>
              <span className={`observability-status ${container.status === 'running' ? 'status-running' : 'status-stopped'}`}>
                {container.status}
              </span>
            </button>
          ))}
        </section>

        <section className="inventory-detail" aria-label="Selected container details">
          {!selectedId && (
            <p className="observability-muted">Select a container to view its evidence.</p>
          )}

          {detailLoading && (
            <p className="observability-muted">Loading container evidence…</p>
          )}

          {detailError && (
            <div className="observability-error">{detailError}</div>
          )}

          {detail && !detailLoading && detail.id === selectedId && (
            <>
              <div className="observability-card-header">
                <div>
                  <p className="observability-label">SELECTED CONTAINER</p>
                  <h2>{detail.container}</h2>
                  <p className="observability-muted">{detail.image}</p>
                </div>
                <span className={`observability-status ${detail.status === 'running' ? 'status-running' : 'status-stopped'}`}>
                  {detail.status}
                </span>
              </div>

              <div className="observability-metrics">
                <Metric label="Exit code" value={detail.exit_code} />
                <Metric label="Restarts" value={detail.restart_count} />
                <Metric label="Health check" value={detail.health || 'Not configured'} />
              </div>

              <section className="observability-analysis observability-assessment">
                <div className="assessment-heading">
                  <div>
                    <h3>Evidence-based assessment</h3>
                    <p className="observability-muted">
                      Evaluate this container using deterministic rules and its latest saved evidence.
                      This is not a live measurement or a confirmed root-cause analysis.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="observability-run assessment-button"
                    disabled={isAssessingSelected}
                    onClick={() => assessContainer(selectedId)}
                  >
                    {isAssessingSelected ? 'Assessing…' : 'Assess container'}
                  </button>
                </div>

                {selectedAssessmentError && (
                  <div className="observability-error" role="alert">
                    {selectedAssessmentError}
                  </div>
                )}

                {selectedAssessment && !isAssessingSelected && (
                  <div className="assessment-result" aria-live="polite">
                    <div className="assessment-result-header">
                      <span className={`assessment-severity severity-${selectedAssessment.severity || 'info'}`}>
                        {(selectedAssessment.severity || 'info').toUpperCase()} SEVERITY
                      </span>
                      <span className="observability-muted">
                        Confidence: {selectedAssessment.confidence || 'unknown'}
                      </span>
                    </div>

                    <p>{selectedAssessment.diagnosis}</p>

                    <section className="assessment-section">
                      <h4>Findings</h4>
                      {selectedAssessment.findings?.length ? (
                        <ul>
                          {selectedAssessment.findings.map((item, index) => (
                            <li key={`finding-${selectedId}-${index}`}>{item.replaceAll('_', ' ')}</li>
                          ))}
                        </ul>
                      ) : <p className="observability-muted">No decisive findings in the available evidence.</p>}
                    </section>

                    <section className="assessment-section">
                      <h4>Observations</h4>
                      {selectedAssessment.observations?.length ? (
                        <ul>
                          {selectedAssessment.observations.map((item, index) => (
                            <li key={`assessment-observation-${selectedId}-${index}`}>{item}</li>
                          ))}
                        </ul>
                      ) : <p>No observations returned.</p>}
                    </section>

                    <section className="assessment-section">
                      <h4>Recommendations</h4>
                      {selectedAssessment.recommendations?.length ? (
                        <ul>
                          {selectedAssessment.recommendations.map((item, index) => (
                            <li key={`assessment-recommendation-${selectedId}-${index}`}>{item}</li>
                          ))}
                        </ul>
                      ) : <p>No recommendations returned.</p>}
                    </section>

                    {selectedAssessment.limitations?.length > 0 && (
                      <details className="observability-evidence">
                        <summary>Assessment limitations</summary>
                        <div className="assessment-limitations-list">
                          {selectedAssessment.limitations.map((item, index) => (
                            <p key={`assessment-limitation-${selectedId}-${index}`}>
                              {item}
                            </p>
                          ))}
                        </div>
                      </details>
                    )}

                    <p className="observability-muted">
                      Evidence collected: {selectedAssessment.evidence_collected_at
                        ? new Date(selectedAssessment.evidence_collected_at).toLocaleString()
                        : 'Unknown'}
                    </p>
                  </div>
                )}
              </section>

              <section className="observability-analysis observability-resource-section">
                <h3>Resource metrics</h3>
                {metrics?.available ? (
                  <div className="observability-resource-grid">
                    <Metric label="CPU usage" value={metrics.cpu_percent} />
                    <Metric label="Memory usage" value={metrics.memory_usage} />
                    <Metric label="Memory percentage" value={metrics.memory_percent} />
                    <Metric label="Network I/O (in / out)" value={metrics.network_io} />
                    <Metric label="Block I/O (read / write)" value={metrics.block_io} />
                    <Metric label="Processes (PIDs)" value={metrics.pids} />
                  </div>
                ) : (
                  <p className="observability-muted">
                    {metrics?.reason || 'Resource metrics are unavailable in this snapshot.'}
                  </p>
                )}
              </section>

              <section className="observability-analysis">
                <h3>Evidence-based assessment</h3>
                <p>
                  {detail.status === 'running'
                    ? 'The container was running when this snapshot was collected. This alone does not establish application health.'
                    : detail.exit_code === 0
                      ? 'The container has exited with code 0. This is not by itself evidence of a failure; check its intended workload and logs.'
                      : `The container has exited with code ${detail.exit_code ?? 'unknown'}. Inspect its logs and expected workload to determine the cause.`}
                </p>
                {detail.restart_count > 0 && (
                  <p>
                    The snapshot reports {detail.restart_count} restart(s). Review timestamps and logs to determine whether restarts are unexpected.
                  </p>
                )}
                <p className="observability-muted">
                  Evidence source: {detail.evidence_source || 'Saved diagnostics snapshot'}
                </p>
              </section>

              <section className="observability-analysis">
                <h3>Lifecycle</h3>
                <div className="observability-resource-grid">
                  <Metric label="Created" value={detail.created ? new Date(detail.created).toLocaleString() : '—'} />
                  <Metric label="Started" value={detail.started_at && !detail.started_at.startsWith('0001-') ? new Date(detail.started_at).toLocaleString() : '—'} />
                  <Metric label="Finished" value={detail.finished_at && !detail.finished_at.startsWith('0001-') ? new Date(detail.finished_at).toLocaleString() : '—'} />
                  <Metric label="Snapshot collected" value={detail.collected_at ? new Date(detail.collected_at).toLocaleString() : '—'} />
                </div>
              </section>

              <details className="observability-evidence">
                <summary>View collected logs</summary>
                <pre>{detail.logs || 'No logs available.'}</pre>
              </details>

              <details className="observability-evidence">
                <summary>View container labels</summary>
                <pre>{JSON.stringify(detail.labels || {}, null, 2)}</pre>
              </details>

              <p className="observability-muted">
                Container ID: {detail.id}
              </p>
            </>
          )}
        </section>
      </div>

      <section className="observability-analysis legacy-diagnoses">
        <h2>Diagnostic test cases</h2>
        <p className="observability-muted">
          These existing allowlisted tests are retained to validate Lumora's deterministic diagnosis behavior.
        </p>
        <div className="observability-grid">
          {targets.map(({ id, label }) => {
            const result = results[id]
            const currentAnalysis = analysis(id)
            const isRunning = result?.evidence?.status === 'running'
            return (
              <article className="observability-card" key={id}>
                <div className="observability-card-header">
                  <div>
                    <p className="observability-label">TEST CONTAINER</p>
                    <h2>{label}</h2>
                  </div>
                  {result && (
                    <span className={`observability-status ${isRunning ? 'status-running' : 'status-stopped'}`}>
                      {result.evidence.status}
                    </span>
                  )}
                </div>

                {diagnosisLoading[id] && (
                  <p className="observability-muted">Loading diagnostic evidence…</p>
                )}
                {diagnosisErrors[id] && (
                  <div className="observability-error">{diagnosisErrors[id]}</div>
                )}

                {result && !diagnosisLoading[id] && (
                  <>
                    <div className="observability-metrics">
                      <Metric label="Exit code" value={result.evidence.exit_code} />
                      <Metric label="Restarts" value={result.evidence.restart_count} />
                      <Metric label="Confidence" value={currentAnalysis?.confidence} />
                    </div>
                    <section className="observability-analysis">
                      <h3>Diagnosis</h3>
                      <p>{currentAnalysis?.diagnosis || 'No diagnosis available.'}</p>
                    </section>
                    <section className="observability-analysis">
                      <h3>Observations</h3>
                      {currentAnalysis?.observations?.length ? (
                        <ul>{currentAnalysis.observations.map((item, index) => (
                          <li key={`${id}-observation-${index}`}>{item}</li>
                        ))}</ul>
                      ) : <p>No observations returned.</p>}
                    </section>
                    <section className="observability-analysis">
                      <h3>Recommendations</h3>
                      {currentAnalysis?.recommendations?.length ? (
                        <ul>{currentAnalysis.recommendations.map((item, index) => (
                          <li key={`${id}-recommendation-${index}`}>{item}</li>
                        ))}</ul>
                      ) : <p>No recommendations returned.</p>}
                    </section>
                    <details className="observability-evidence">
                      <summary>View test logs</summary>
                      <pre>{result.evidence.logs || 'No logs available.'}</pre>
                    </details>
                    <p className="observability-muted">
                      Snapshot: {result.collected_at ? new Date(result.collected_at).toLocaleString() : 'Unknown'}
                    </p>
                  </>
                )}

                <button
                  className="observability-run"
                  disabled={Boolean(diagnosisLoading[id])}
                  onClick={() => diagnose(id)}
                >
                  {diagnosisLoading[id] ? 'Investigating…' : 'Run diagnosis'}
                </button>
              </article>
            )
          })}
        </div>
      </section>
    </section>
  )
}

export default DevOps
