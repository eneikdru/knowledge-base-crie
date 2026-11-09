<script>
  import { onMount } from 'svelte';

  export let apiBaseUrl = '';

  let query = '';
  let status = 'idle'; // 'idle' | 'loading' | 'success' | 'error'
  let documents = [];
  let errorMessage = '';
  let totalCount = 0;

  async function fetchDocuments(searchQuery = '') {
    status = 'loading';
    errorMessage = '';
    try {
      const url = `${apiBaseUrl}/api/search?q=${encodeURIComponent(searchQuery)}`;
      const response = await fetch(url, {
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const items = Array.isArray(data) ? data : (data.items || data.documents || data.results || []);
      documents = items;
      totalCount = typeof data.total === 'number' ? data.total : items.length;
      status = 'success';
    } catch (err) {
      status = 'error';
      errorMessage = err.message || 'Unable to connect to the document search service.';
      documents = [];
      totalCount = 0;
    }
  }

  function handleSearch(event) {
    if (event) event.preventDefault();
    fetchDocuments(query);
  }

  function handleRetry() {
    fetchDocuments(query);
  }

  onMount(() => {
    fetchDocuments('');
  });
</script>

<main class="catalog-container">
  <header class="catalog-header">
    <h1>Knowledge Base Catalog</h1>
    <p class="subtitle">Search and browse normative and educational documentation</p>
    <form class="search-form" on:submit={handleSearch} role="search">
      <label for="catalog-search-input" class="visually-hidden">Search materials</label>
      <input
        id="catalog-search-input"
        type="search"
        bind:value={query}
        placeholder="Search materials by title, author, or keyword..."
        aria-label="Search materials"
      />
      <button type="submit" class="btn-search" disabled={status === 'loading'}>
        {status === 'loading' ? 'Searching...' : 'Search'}
      </button>
    </form>
  </header>

  <section class="catalog-content" aria-live="polite">
    {#if status === 'loading'}
      <div class="state-view loading-state" role="status" aria-busy="true">
        <div class="spinner" aria-hidden="true"></div>
        <p>Loading catalog materials...</p>
      </div>
    {:else if status === 'error'}
      <div class="state-view error-state" role="alert">
        <div class="error-icon" aria-hidden="true">!</div>
        <h2>Unable to load materials</h2>
        <p class="error-message">{errorMessage}</p>
        <p class="retry-guidance">Please check your backend connection or try again shortly.</p>
        <button type="button" class="btn-retry" on:click={handleRetry}>Retry Search</button>
      </div>
    {:else if status === 'success' && documents.length === 0}
      <div class="state-view empty-state" data-testid="empty-state">
        <h2>No materials found</h2>
        <p>Showing 0 materials</p>
        <p class="empty-hint">No domain records matched your query or the catalog is currently empty.</p>
      </div>
    {:else if status === 'success' && documents.length > 0}
      <div class="state-view present-state" data-testid="present-state">
        <div class="results-meta">
          <span>Showing 1-{documents.length} of {totalCount} materials</span>
        </div>
        <div class="document-grid" role="list">
          {#each documents as doc (doc.id || doc.url || doc.title)}
            <article class="document-card" role="listitem">
              <h3 class="doc-title">{doc.title || 'Untitled Document'}</h3>
              {#if doc.author}
                <p class="doc-author"><strong>Author:</strong> {doc.author}</p>
              {/if}
              {#if doc.date || doc.created_at}
                <p class="doc-date"><strong>Date:</strong> {doc.date || doc.created_at}</p>
              {/if}
              {#if doc.description}
                <p class="doc-description">{doc.description}</p>
              {/if}
              <div class="card-actions">
                {#if doc.download_url || doc.url}
                  <a
                    href={doc.download_url || doc.url}
                    class="btn-download"
                    download
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Download
                  </a>
                {/if}
              </div>
            </article>
          {/each}
        </div>
      </div>
    {/if}
  </section>
</main>

<style>
  .catalog-container {
    max-width: 1040px;
    margin: 0 auto;
    padding: 2rem 1rem;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1a202c;
  }
  .catalog-header {
    margin-bottom: 2rem;
  }
  .catalog-header h1 {
    margin: 0 0 0.5rem;
    font-size: 2rem;
    font-weight: 700;
  }
  .subtitle {
    margin: 0 0 1.5rem;
    color: #4a5568;
  }
  .search-form {
    display: flex;
    gap: 0.75rem;
  }
  .search-form input[type='search'] {
    flex: 1;
    padding: 0.75rem 1rem;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    font-size: 1rem;
  }
  .btn-search, .btn-retry, .btn-download {
    background-color: #2b6cb0;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .btn-search:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .state-view {
    padding: 3rem 1.5rem;
    border-radius: 8px;
    text-align: center;
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
  }
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }
  .spinner {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid #e2e8f0;
    border-top-color: #2b6cb0;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  .error-state {
    background-color: #fff5f5;
    border-color: #feb2b2;
    color: #9b2c2c;
  }
  .error-icon {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
  }
  .error-message {
    font-weight: 600;
    margin: 0.5rem 0;
  }
  .retry-guidance {
    color: #4a5568;
    margin-bottom: 1.5rem;
  }
  .empty-state h2 {
    margin-bottom: 0.5rem;
  }
  .empty-hint {
    color: #718096;
    font-size: 0.95rem;
  }
  .present-state {
    text-align: left;
    background: transparent;
    border: none;
    padding: 0;
  }
  .results-meta {
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
    color: #4a5568;
  }
  .document-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.25rem;
  }
  .document-card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.25rem;
    background-color: #ffffff;
    display: flex;
    flex-direction: column;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
  .doc-title {
    margin: 0 0 0.5rem;
    font-size: 1.2rem;
    color: #2d3748;
  }
  .doc-author, .doc-date {
    margin: 0.25rem 0;
    font-size: 0.875rem;
    color: #4a5568;
  }
  .doc-description {
    margin: 0.75rem 0 1rem;
    font-size: 0.9rem;
    color: #718096;
    flex: 1;
  }
  .card-actions {
    margin-top: auto;
  }
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }
</style>
