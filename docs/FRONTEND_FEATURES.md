# Frontend Features: Auth, Memories, Documents & Voice Transcription

This guide covers authentication and features to add to the existing chat/voice UI.

---

## 1. Supabase Authentication

### Setup

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://sbviochhmnjwaszqnwcd.supabase.co',
  'your_anon_key'  // Public anon key (safe for frontend)
)
```

### Auth Functions

```typescript
// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

// Get current session (includes JWT token)
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// Sign out
await supabase.auth.signOut()

// Listen for auth changes
supabase.auth.onAuthStateChange((event, session) => {
  if (session) {
    // User logged in - store token
    setToken(session.access_token)
  } else {
    // User logged out
    setToken(null)
  }
})
```

### Making Authenticated API Calls

```typescript
const API_BASE = "http://localhost:8000";

async function apiCall(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session?.access_token}`,
    },
  })
}
```

---

## 2. API Endpoints (Authenticated)

All `/me/*` endpoints require Bearer token authentication.

### User Info

```typescript
// Get current user info
GET /me
Headers: { Authorization: "Bearer <token>" }

Response: {
  user_id: "uuid-123",
  email: "user@example.com",
  role: "authenticated",
  thread_id: "t-abc123"  // null if no thread yet
}
```

### Documents (User's Private)

```typescript
// Upload document (private to authenticated user)
POST /me/documents
Headers: { Authorization: "Bearer <token>" }
Content-Type: multipart/form-data
Body: { file: File, description?: string }

Response: {
  status: "uploaded",
  document_id: "doc-001",
  filename: "my_project.pdf",
  thread_id: "t-abc123",
  scope: "user"
}

// List my documents
GET /me/documents
Headers: { Authorization: "Bearer <token>" }

Response: {
  documents: [
    { document_id: "doc-001", filename: "my_project.pdf", description: "..." }
  ],
  thread_id: "t-abc123"
}
```

### Memories

```typescript
// List my memories (facts the assistant remembers about me)
GET /me/memories
Headers: { Authorization: "Bearer <token>" }

Response: {
  memories: [
    { memory_id: "mem-001", content: "User is on Team Alpha", metadata: {} },
    { memory_id: "mem-002", content: "User prefers Python", metadata: {} }
  ],
  thread_id: "t-abc123",
  user_id: "uuid-123"
}

// Delete a memory
DELETE /me/memories/{memory_id}
Headers: { Authorization: "Bearer <token>" }

Response: { status: "deleted", memory_id: "mem-001" }
```

---

## 2. UI Components

### Sidebar Layout

Add these sections to the existing sidebar (below threads):

```
┌─────────────────┐
│ Threads         │  ← existing
│ ...             │
├─────────────────┤
│ My Documents    │  ← NEW
│                 │
│ 📄 project.pdf  │
│ 📄 notes.md     │
│                 │
│ [+ Upload]      │
├─────────────────┤
│ Memories        │  ← NEW
│                 │
│ • Team Alpha    │  [×]
│ • Python dev    │  [×]
│ • AI project    │  [×]
│                 │
└─────────────────┘
```

### Document Upload Component

```tsx
function DocumentUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File) => {
    setUploading(true);
    const form = new FormData();
    form.append("file", file);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_BASE}/me/documents`, {
        method: "POST",
        headers: { 'Authorization': `Bearer ${session?.access_token}` },
        body: form,
      });
      const data = await res.json();
      // Refresh document list
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md,.json,.yaml"
        hidden
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? "Uploading..." : "+ Upload Document"}
      </button>
    </div>
  );
}
```

### Documents List Component

```tsx
function DocumentsList() {
  const [docs, setDocs] = useState<Document[]>([]);

  const fetchDocs = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    const res = await fetch(`${API_BASE}/me/documents`, {
      headers: { 'Authorization': `Bearer ${session?.access_token}` }
    });
    const data = await res.json();
    setDocs(data.documents || []);
  };

  useEffect(() => { fetchDocs(); }, []);

  return (
    <div className="documents-list">
      <h3>My Documents</h3>
      {docs.length === 0 ? (
        <p className="empty">No documents uploaded</p>
      ) : (
        <ul>
          {docs.map(doc => (
            <li key={doc.document_id}>
              <span className="icon">📄</span>
              <span className="filename">{doc.filename}</span>
            </li>
          ))}
        </ul>
      )}
      <DocumentUpload />
    </div>
  );
}
```

### Memories List Component

```tsx
function MemoriesList() {
  const [memories, setMemories] = useState<Memory[]>([]);

  const fetchMemories = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    const res = await fetch(`${API_BASE}/me/memories`, {
      headers: { 'Authorization': `Bearer ${session?.access_token}` }
    });
    const data = await res.json();
    setMemories(data.memories || []);
  };

  useEffect(() => { fetchMemories(); }, []);

  const deleteMemory = async (memoryId: string) => {
    const { data: { session } } = await supabase.auth.getSession();
    await fetch(`${API_BASE}/me/memories/${memoryId}`, {
      method: "DELETE",
      headers: { 'Authorization': `Bearer ${session?.access_token}` }
    });
    fetchMemories();
  };

  return (
    <div className="memories-list">
      <h3>Memories</h3>
      {memories.length === 0 ? (
        <p className="empty">No memories yet</p>
      ) : (
        <ul>
          {memories.map(mem => (
            <li key={mem.memory_id}>
              <span className="content">{mem.content}</span>
              <button
                className="delete-btn"
                onClick={() => deleteMemory(mem.memory_id)}
                title="Delete memory"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## 3. Voice Mode: Display Conversation in Chat

**Important:** During voice mode, show the conversation as text in the chat window while audio plays. Users should see AND hear the conversation.

### WebSocket Message Handling

In voice mode, handle these messages to display text:

```typescript
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.type) {
    // === AUDIO (existing) ===
    case "audio_out":
      // Queue for playback (existing logic)
      queueAudioForPlayback(msg.audio, msg.sample_rate);
      break;

    // === TEXT DISPLAY (add these) ===
    case "transcript":
      if (msg.final) {
        // Final transcript - add as user message in chat
        addMessageToChat({
          role: "user",
          content: msg.text
        });
      } else {
        // Interim transcript - show in typing indicator
        updateInterimTranscript(msg.text);
      }
      break;

    case "response":
      // Assistant's response text - add to chat
      // This arrives while audio_out is also streaming
      addMessageToChat({
        role: "assistant",
        content: msg.text
      });
      break;
  }
};
```

### Visual Flow

```
User speaks → transcript (final: false) → "What's the dead..."  [interim indicator]
           → transcript (final: true)  → [User]: "What's the deadline?"

Server responds → response            → [AURA]: "The deadline is Sunday 5pm..."
               → audio_out (chunk 1)  → 🔊 Playing...
               → audio_out (chunk 2)  → 🔊 Playing...
               → audio_out (chunk 3)  → 🔊 Playing...
```

### Chat Display During Voice Mode

```tsx
function ChatWindow({ messages, interimTranscript, isVoiceMode }) {
  return (
    <div className="chat-window">
      {/* Existing messages */}
      {messages.map((msg, i) => (
        <div key={i} className={`message ${msg.role}`}>
          <span className="role">{msg.role === "user" ? "You" : "AURA"}</span>
          <p>{msg.content}</p>
        </div>
      ))}

      {/* Interim transcript (voice mode only) */}
      {isVoiceMode && interimTranscript && (
        <div className="message user interim">
          <span className="role">You</span>
          <p className="typing">{interimTranscript}...</p>
        </div>
      )}
    </div>
  );
}
```

### State Management

```typescript
const [messages, setMessages] = useState<Message[]>([]);
const [interimTranscript, setInterimTranscript] = useState<string>("");

// In WebSocket handler:
case "transcript":
  if (msg.final) {
    setInterimTranscript("");  // Clear interim
    setMessages(prev => [...prev, { role: "user", content: msg.text }]);
  } else {
    setInterimTranscript(msg.text);  // Update interim
  }
  break;

case "response":
  setMessages(prev => [...prev, { role: "assistant", content: msg.text }]);
  break;
```

---

## 4. Type Definitions

```typescript
interface Document {
  document_id: string;
  filename: string;
  description?: string;
  created_at?: string;
}

interface Memory {
  memory_id: string;
  content: string;
  metadata?: Record<string, any>;
  created_at?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}
```

---

## 5. Styling Suggestions

```css
/* Documents list */
.documents-list ul {
  list-style: none;
  padding: 0;
}

.documents-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
}

.documents-list li:hover {
  background: rgba(0,0,0,0.05);
}

/* Memories list */
.memories-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  font-size: 14px;
}

.memories-list .delete-btn {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
}

.memories-list li:hover .delete-btn {
  opacity: 1;
}

/* Interim transcript */
.message.interim p {
  color: #666;
  font-style: italic;
}

/* Empty states */
.empty {
  color: #999;
  font-size: 13px;
  text-align: center;
  padding: 16px;
}
```

---

## Summary

| Feature | Endpoint | Auth Required | UI Location |
|---------|----------|---------------|-------------|
| Get current user | `GET /me` | Yes | App init |
| Upload document | `POST /me/documents` | Yes | Sidebar → My Documents |
| List documents | `GET /me/documents` | Yes | Sidebar → My Documents |
| List memories | `GET /me/memories` | Yes | Sidebar → Memories |
| Delete memory | `DELETE /me/memories/{mid}` | Yes | Memory item × button |
| Voice transcript | WebSocket `transcript` message | Via user_id | Chat window (user bubble) |
| Voice response | WebSocket `response` message | Via user_id | Chat window (assistant bubble) |

## Auth Flow

```
1. User opens app
2. Check Supabase session → supabase.auth.getSession()
3. If no session → Show login/signup form
4. If session exists → Get JWT token from session.access_token
5. Include token in all /me/* API calls
6. WebSocket: pass token as query param → /ws?mode=chat&token=<JWT>
```

## WebSocket Connection (with Auth)

```typescript
// Connect to WebSocket with Supabase token
async function connectWebSocket(mode: 'chat' | 'voice' = 'chat') {
  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    throw new Error('Not authenticated');
  }

  const token = session.access_token;
  const ws = new WebSocket(
    `${WS_BASE}/ws?mode=${mode}&token=${encodeURIComponent(token)}`
  );

  return ws;
}

// Usage
const ws = await connectWebSocket('chat');
ws.onmessage = (e) => { /* handle messages */ };
```
