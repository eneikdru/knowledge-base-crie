<script>
  let query = '';
  let activeTab = 'overview';
  let telemetry = [
    { label: 'Active Nodes', value: '1,420', change: '+12.4%', status: 'positive' },
    { label: 'Index Latency', value: '28ms', change: '-4.1%', status: 'positive' },
    { label: 'Sync Status', value: '99.98%', change: 'Optimal', status: 'neutral' },
    { label: 'Error Rate', value: '0.02%', change: '-0.01%', status: 'positive' }
  ];

  let searchResults = [
    { id: 1, title: 'Knowledge Base Synchronization Architecture', tag: 'Architecture', updated: '10m ago' },
    { id: 2, title: 'Telemetry Ingestion & Event Stream Protocols', tag: 'Protocol', updated: '1h ago' },
    { id: 3, title: 'Edge Deployment Resilience & Failover Policy', tag: 'Operations', updated: '3h ago' }
  ];

  function handleSearch(e) {
    e.preventDefault();
  }
</script>

<main class="app-container">
  <header class="navbar">
    <div class="brand-area">
      <div class="logo-badge">KB</div>
      <span class="brand-title">Knowledge Base</span>
    </div>
    <nav class="nav-links" aria-label="Primary Navigation">
      <button
        type="button"
        class="nav-link"
        class:active={activeTab === 'overview'}
        on:click={() => activeTab = 'overview'}
      >
        Overview
      </button>
      <button
        type="button"
        class="nav-link"
        class:active={activeTab === 'telemetry'}
        on:click={() => activeTab = 'telemetry'}
      >
        Telemetry
      </button>
      <button
        type="button"
        class="nav-link"
        class:active={activeTab === 'documents'}
        on:click={() => activeTab = 'documents'}
      >
        Documents
      </button>
    </nav>
  </header>

  <div class="content-wrapper">
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="page-title">Knowledge Base Dashboard</h1>
        <p class="page-subtitle">Real-time operational telemetry, verified design system tokens, and document repository indexing.</p>
      </div>
      <form class="search-form" on:submit={handleSearch} role="search">
        <label for="kb-search" class="sr-only">Search knowledge base</label>
        <input
          id="kb-search"
          type="search"
          class="search-input"
          placeholder="Search topics, tokens, documents..."
          bind:value={query}
        />
        <button type="submit" class="btn btn-primary">Search</button>
      </form>
    </section>

    <section class="telemetry-section" aria-label="Telemetry Metrics">
      <h2 class="section-title">Live Telemetry</h2>
      <div class="cards-grid">
        {#each telemetry as item}
          <div class="metric-card">
            <span class="metric-label">{item.label}</span>
            <div class="metric-value-row">
              <span class="metric-value">{item.value}</span>
              <span class="metric-badge {item.status}">{item.change}</span>
            </div>
          </div>
        {/each}
      </div>
    </section>

    <section class="entries-section" aria-label="Recent Documents">
      <h2 class="section-title">Recent Records</h2>
      <div class="entries-list">
        {#each searchResults as item (item.id)}
          <article class="entry-card">
            <div class="entry-header">
              <span class="entry-tag">{item.tag}</span>
              <time class="entry-updated">{item.updated}</time>
            </div>
            <h3 class="entry-title">{item.title}</h3>
            <div class="entry-actions">
              <button type="button" class="btn btn-outline">View Entry</button>
            </div>
          </article>
        {/each}
      </div>
    </section>
  </div>
</main>

<style>
  :root {
    --color-bg-canvas: #0b0f19;
    --color-bg-surface: #111827;
    --color-bg-card: #1f2937;
    --color-border: #374151;
    --color-border-hover: #4b5563;
    --color-text-primary: #f9fafb;
    --color-text-secondary: #9ca3af;
    --color-text-muted: #6b7280;
    --color-brand-primary: #3b82f6;
    --color-brand-hover: #2563eb;
    --color-status-success: #10b981;
    --color-status-success-bg: rgba(16, 185, 129, 0.12);
    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  }

  :global(*),
  :global(*::before),
  :global(*::after) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    background-color: var(--color-bg-canvas);
    color: var(--color-text-primary);
    font-family: var(--font-family);
    line-height: 1.5;
    min-width: 320px;
    overflow-x: hidden;
  }

  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: 100vw;
    overflow-x: hidden;
  }

  .navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.5rem;
    background-color: var(--color-bg-surface);
    border-bottom: 1px solid var(--color-border);
    flex-wrap: wrap;
    gap: 1rem;
  }

  .brand-area {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-badge {
    background-color: var(--color-brand-primary);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.875rem;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
  }

  .brand-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .nav-link {
    background: transparent;
    border: none;
    color: var(--color-text-secondary);
    padding: 0.625rem 0.875rem;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 0.375rem;
    cursor: pointer;
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .nav-link:hover {
    background-color: var(--color-bg-card);
    color: var(--color-text-primary);
  }

  .nav-link.active {
    background-color: var(--color-bg-card);
    color: var(--color-brand-primary);
    font-weight: 600;
  }

  .content-wrapper {
    flex: 1;
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .hero-section {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .page-title {
    font-size: 1.875rem;
    font-weight: 700;
    color: var(--color-text-primary);
    letter-spacing: -0.02em;
  }

  .page-subtitle {
    color: var(--color-text-secondary);
    font-size: 1rem;
    max-width: 640px;
    margin-top: 0.25rem;
  }

  .search-form {
    display: flex;
    gap: 0.75rem;
    max-width: 640px;
    width: 100%;
    flex-wrap: wrap;
  }

  .search-input {
    flex: 1 1 240px;
    min-height: 44px;
    padding: 0.625rem 1rem;
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    color: var(--color-text-primary);
    font-size: 0.9375rem;
    outline: none;
    transition: border-color 0.15s ease;
  }

  .search-input:focus {
    border-color: var(--color-brand-primary);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    padding: 0.625rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 600;
    border-radius: 0.5rem;
    cursor: pointer;
    border: 1px solid transparent;
    transition: background-color 0.15s ease, border-color 0.15s ease;
  }

  .btn-primary {
    background-color: var(--color-brand-primary);
    color: #ffffff;
  }

  .btn-primary:hover {
    background-color: var(--color-brand-hover);
  }

  .btn-outline {
    background-color: transparent;
    border-color: var(--color-border);
    color: var(--color-text-primary);
  }

  .btn-outline:hover {
    border-color: var(--color-border-hover);
    background-color: var(--color-bg-card);
  }

  .section-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--color-text-primary);
  }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }

  .metric-card {
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .metric-label {
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .metric-value-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-text-primary);
  }

  .metric-badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 9999px;
  }

  .metric-badge.positive {
    background-color: var(--color-status-success-bg);
    color: var(--color-status-success);
  }

  .metric-badge.neutral {
    background-color: rgba(156, 163, 175, 0.12);
    color: var(--color-text-secondary);
  }

  .entries-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .entry-card {
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .entry-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .entry-tag {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-brand-primary);
    background-color: rgba(59, 130, 246, 0.1);
    padding: 0.2rem 0.6rem;
    border-radius: 0.25rem;
  }

  .entry-updated {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .entry-title {
    font-size: 1.0625rem;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .entry-actions {
    display: flex;
    justify-content: flex-end;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 640px) {
    .navbar {
      flex-direction: column;
      align-items: flex-start;
      padding: 0.75rem 1rem;
    }

    .content-wrapper {
      padding: 1.25rem 1rem;
    }

    .search-form {
      flex-direction: column;
    }

    .search-input {
      width: 100%;
    }

    .btn {
      width: 100%;
    }

    .cards-grid {
      grid-template-columns: 1fr;
    }
  }
</style>