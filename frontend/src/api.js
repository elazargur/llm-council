/**
 * API client for the LLM Council backend.
 * Uses relative paths for Vercel deployment.
 */

// Get auth credentials from sessionStorage
function getAuthHeaders() {
  const password = sessionStorage.getItem('auth_password') || '';
  const email = sessionStorage.getItem('auth_email') || '';
  return {
    'X-Auth-Password': password,
    'X-Auth-Email': email,
  };
}

export const api = {
  /**
   * Get available models and defaults.
   */
  async getModels() {
    const response = await fetch('/api/models', {
      headers: {
        ...getAuthHeaders(),
      },
    });
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized');
      }
      throw new Error('Failed to get models');
    }
    return response.json();
  },

  /**
   * Run the council with streaming updates.
   * @param {string} content - The user's query
   * @param {object} modelConfig - Model configuration { councilModels, chairmanModel }
   * @param {string} sessionId - Optional session ID to save conversation to
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async runCouncilStream(content, modelConfig, sessionId, onEvent) {
    const body = { content };
    if (modelConfig?.councilModels?.length > 0) {
      body.council_models = modelConfig.councilModels;
    }
    if (modelConfig?.chairmanModel) {
      body.chairman_model = modelConfig.chairmanModel;
    }
    if (sessionId) {
      body.session_id = sessionId;
    }

    const response = await fetch('/api/council', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized');
      }
      throw new Error('Failed to run council');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Check if user is authenticated by making a test request.
   */
  async checkAuth() {
    try {
      await this.getModels();
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Store auth credentials in sessionStorage.
   */
  setAuth(password, email) {
    sessionStorage.setItem('auth_password', password);
    sessionStorage.setItem('auth_email', email);
  },

  /**
   * Clear auth credentials.
   */
  clearAuth() {
    sessionStorage.removeItem('auth_password');
    sessionStorage.removeItem('auth_email');
  },

  /**
   * Check if credentials are stored.
   */
  hasStoredAuth() {
    return !!(sessionStorage.getItem('auth_password') && sessionStorage.getItem('auth_email'));
  },

  // ============== SESSION METHODS ==============

  /**
   * Get list of user's sessions (summary only).
   */
  async getSessions() {
    const response = await fetch('/api/sessions', {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
      throw new Error('Failed to get sessions');
    }
    return response.json();
  },

  /**
   * Get a single session with full messages.
   */
  async getSession(sessionId) {
    const response = await fetch(`/api/sessions/${sessionId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
      if (response.status === 404) throw new Error('Session not found');
      throw new Error('Failed to get session');
    }
    return response.json();
  },

  /**
   * Create a new session.
   */
  async createSession() {
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
      throw new Error('Failed to create session');
    }
    return response.json();
  },

  /**
   * Delete a session.
   */
  async deleteSession(sessionId) {
    const response = await fetch(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
      throw new Error('Failed to delete session');
    }
    return response.json();
  },
};
