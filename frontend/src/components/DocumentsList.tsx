import { useState, useEffect, useRef } from 'react'
import { apiCall } from '../lib/supabase'

interface Document {
  document_id: string
  filename: string
  description?: string
  created_at?: string
}

interface DocumentsListProps {
  isCollapsed: boolean
}

export function DocumentsList({ isCollapsed }: DocumentsListProps) {
  const [docs, setDocs] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchDocuments = async () => {
    try {
      const res = await apiCall('/me/documents')
      const data = await res.json()
      setDocs(data.documents || [])
    } catch (error) {
      console.error('Failed to fetch documents:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  const handleUpload = async (file: File) => {
    setUploading(true)
    const form = new FormData()
    form.append('file', file)

    try {
      const res = await apiCall('/me/documents', {
        method: 'POST',
        body: form,
      })
      if (res.ok) {
        fetchDocuments()
      }
    } catch (error) {
      console.error('Failed to upload document:', error)
    } finally {
      setUploading(false)
    }
  }

  if (isCollapsed) {
    return (
      <div className="sidebar-section collapsed">
        <div className="section-icon" title="Documents">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
          </svg>
        </div>
      </div>
    )
  }

  return (
    <div className="sidebar-section documents-section">
      <div className="section-header">
        <h3>Documents</h3>
        <span className="section-count">{docs.length}</span>
      </div>

      <div className="section-content">
        {loading ? (
          <div className="section-loading">Loading...</div>
        ) : docs.length === 0 ? (
          <div className="section-empty">No documents uploaded</div>
        ) : (
          <ul className="documents-list">
            {docs.map(doc => (
              <li key={doc.document_id} className="document-item">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" className="doc-icon">
                  <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
                </svg>
                <span className="doc-filename">{doc.filename}</span>
              </li>
            ))}
          </ul>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,.json,.yaml"
          hidden
          onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        />
        <button
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : '+ Upload'}
        </button>
      </div>
    </div>
  )
}
