<script>
  import { onMount } from 'svelte';

  let searchQuery = '';
  let selectedCategory = 'all';
  let activeTab = 'articles';

  let telemetry = {
    activeNodes: 42,
    queryLatencyMs: 14,
    syncStatus: 'Optimal',
    uptimePct: 99.99
  };

  let articles = [
    {
      id: 'kb-101',
      title: 'Architectural Invariants & Distributed Consensus',
      category: 'Architecture',
      date: '2026-11-08',
      snippet: 'Core invariants governing multi-region consensus nodes, state replication protocols, and deterministic leader elections.'
    },
    {
      id: 'kb-102',
      title: 'Design System Tokens & Accessibility Standards',
      category: 'Design',
      date: '2026-11-09',
      snippet: 'Specification for WCAG 2.1 AAA contrast ratios, typography scale, focus rings, and dark/light token hierarchies.'
    },
    {
      id: 'kb-103',
      title: 'Telemetry Pipeline & Operational Health Metrics',
      category: 'Telemetry',
      date: '2026-11-10',
      snippet: 'Streaming telemetry ingest, rolling window latency calculations, and automated anomaly detection bounds.'
    }
  ];

  $: filteredArticles = articles.filter(article => {
    const matchesCategory = selectedCategory === 'all' || article.category.toLowerCase() === selectedCategory.toLowerCase();
    const matchesQuery = article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         article.snippet.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesQuery;
  });
</script>

<div class="app-container">
  <header class="navbar" role="banner">
    <div class="brand">
      <span class="brand-badge" aria-hidden="true">KB</span>
      <h1 class="brand-title">Knowledge Base</h1>
    </div>
    <nav class="nav-links" aria-label="Primary Navigation">
      <button
        class="nav-item" 
        class:active={activeTab === 'articles'}
        on:click={() => activeTab = 'articles'}
        aria-current={activeTab === 'articles' ? 'page' : undefined}
      >
        Articles
      </button>
      <button
        class="nav-item" 
        class:active={activeTab === 'telemetry'}
        on:click={() => activeTab = 'telemetry'}
        aria-current={activeTab === 'telemetry' ? 'page' : undefined}
      >
        Telemetry
      </button>
    </nav>
  </header>

  <main class="main-content" id="main-content" role="main">
    <section class="telemetry-bar" aria-label="Operational Telemetry">
      <div class="metric-card">
        <span class="metric-label">Active Nodes</span>
        <span class="metric-value">{telemetry.activeNodes}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Query Latency</span>
        <span class="metric-value">{telemetry.queryLatencyMs} <abbr title="milliseconds">ms</abbr></span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Sync Status</span>
        <span class="metric-value status-optimal">{telemetry.syncStatus}</span>
      </div>
      <div class="metric-card">
        <span class="metric-label">Uptime</span>
        <span class="metric-value">{telemetry.uptimePct}%</span>
      </div>
    </section>

    <section class="search-section" aria-label="Search and Filters">
      <div class="search-box">
        <label for="kb-search" class="visually-hidden">Search knowledge base</label>
        <input
          id="kb-search"
          type="search"
          placeholder="Search topics, specifications, architecture..."
          bind:value={searchQuery}
          class="search-input"
          aria-label="Search topics, specifications, architecture"
        />
      </div>
      <div class="filter-chips" role="group" aria-label="Filter categories">
        <button
          type="button"
          class="chip" 
          class:selected={selectedCategory === 'all'}
          on:click={() => selectedCategory = 'all'}
          aria-pressed={selectedCategory === 'all'}
        >
          All Topics
        </button>
        <button
          type="button"
          class="chip" 
          class:selected={selectedCategory === 'architecture'}
          on:click={() => selectedCategory = 'architecture'}
          aria-pressed={selectedCategory === 'architecture'}
        >
          Architecture
        </button>
        <button
          type="button"
          class="chip" 
          class:selected={selectedCategory === 'design'}
          on:click={() => selectedCategory = 'design'}
          aria-pressed={selectedCategory === 'design'}
        >
          Design
        </button>
        <button
          type="button"
          class="chip" 
          class:selected={selectedCategory === 'telemetry'}
          on:click={() => selectedCategory = 'telemetry'}
          aria-pressed={selectedCategory === 'telemetry'}
        >
          Telemetry
        </button>
      </div>
    </section>

    {#if activeTab === 'articles'}
      <section class="articles-grid" aria-label="Knowledge Base Articles">
        {#if filteredArticles.length === 0}
          <div class="empty-state" role="status">
            <p>No matching knowledge base entries found.</p>
          </div>
        {:else}
          {#each filteredArticles as article (article.id)}
            <article class="article-card" tabindex="0">
              <div class="article-meta">
                <span class="category-tag">{article.category}</span>
                <time datetime={article.date}>{article.date}</time>
              </div>
              <h2 class="article-title">{article.title}</h2>
              <p class="article-snippet">{article.snippet}</p>
              <div class="card-footer">
                <a href="#{article.id}" class="read-link" aria-label="Read article {article.title}">
                  Read document <span aria-hidden="true">&rarr;</span>
                </a>
              </div>
            </article>
          {/each}
        {/if}
      </section>
    {:else}
      <section class="telemetry-detail" aria-label="Detailed System Telemetry">
        <h2>System Telemetry &amp; Health Overview</h2>
        <div class="detail-grid">
          <div class="detail-panel">
            <h3>Cluster Health</h3>
            <p>All ingress nodes reporting nominal latency and zero packet degradation.</p>
          </div>
          <div class="detail-panel">
            <h3>Replication Log</h3>
            <p>Commit index synced across all quorum members with 0 dropped events.</p>
          </div>
        </div>
      </section>
    {/if}
  </main>
</div>

<style>
  :global(:root) {
    --color-bg-base: #0a0e14;
    --color-bg-surface: #111822;
    --color-bg-card: #16202c;
    --color-border: #243447;
    --color-border-focus: #4da3ff;
    --color-text-main: #f0f6fc;
    --color-text-muted: #b1c2d6;
    --color-accent: #3388ff;
    --color-accent-hover: #5ba0ff;
    --color-success: #2ea043;
    --color-badge-bg: #1f334d;
    --color-badge-text: #6cb6ff;
    --font-family-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }

  :global(body) {
    margin: 0;
    background-color: var(--color-bg-base);
    color: var(--color-text-main);
    font-family: var(--font-family-base);
    line-height: 1.5;
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

  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: var(--color-bg-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .brand-badge {
    background-color: var(--color-accent);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.875rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }

  .brand-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0;
    color: var(--color-text-main);
  }

  .nav-links {
    display: flex;
    gap: 0.5rem;
  }

  .nav-item {
    background: transparent;
    border: 1px solid transparent;
    color: var(--color-text-muted);
    font-size: 0.95rem;
    font-weight: 600;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .nav-item:hover {
    color: var(--color-text-main);
    background-color: var(--color-bg-card);
  }

  .nav-item.active {
    color: #ffffff;
    background-color: var(--color-accent);
  }

  .nav-item:focus-visible,
  .chip:focus-visible,
  .search-input:focus-visible,
  .article-card:focus-visible,
  .read-link:focus-visible {
    outline: 2px solid var(--color-border-focus);
    outline-offset: 2px;
  }

  .main-content {
    flex: 1;
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    box-sizing: border-box;
  }

  .telemetry-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .metric-card {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .metric-label {
    font-size: 0.8125rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    font-weight: 600;
  }

  .metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-text-main);
  }

  .metric-value.status-optimal {
    color: #56d364;
  }

  .search-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .search-box {
    width: 100%;
  }

  .search-input {
    width: 100%;
    box-sizing: border-box;
    padding: 0.875rem 1.25rem;
    font-size: 1rem;
    color: var(--color-text-main);
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: 8px;
  }

  .search-input::placeholder {
    color: var(--color-text-muted);
  }

  .filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .chip {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    color: var(--color-text-muted);
    padding: 0.4rem 0.875rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }

  .chip:hover {
    border-color: var(--color-border-focus);
    color: var(--color-text-main);
  }

  .chip.selected {
    background-color: var(--color-badge-bg);
    border-color: var(--color-badge-text);
    color: var(--color-badge-text);
    font-weight: 600;
  }

  .articles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
  }

  .empty-state {
    grid-column: 1 / -1;
    text-align: center;
    padding: 3rem 1rem;
    color: var(--color-text-muted);
    border: 1px dashed var(--color-border);
    border-radius: 8px;
  }

  .article-card {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }

  .article-card:hover {
    transform: translateY(-2px);
    border-color: var(--color-border-focus);
  }

  .article-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    font-size: 0.8125rem;
    color: var(--color-text-muted);
  }

  .category-tag {
    background-color: var(--color-badge-bg);
    color: var(--color-badge-text);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
  }

  .article-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--color-text-main);
    margin: 0 0 0.5rem 0;
    line-height: 1.35;
  }

  .article-snippet {
    font-size: 0.9375rem;
    color: var(--color-text-muted);
    margin: 0 0 1.25rem 0;
    line-height: 1.5;
  }

  .card-footer {
    margin-top: auto;
  }

  .read-link {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    color: var(--color-accent-hover);
    font-weight: 600;
    font-size: 0.875rem;
    text-decoration: none;
  }

  .read-link:hover {
    text-decoration: underline;
  }

  .telemetry-detail {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 2rem;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    margin-top: 1.5rem;
  }

  .detail-panel {
    padding: 1.25rem;
    background-color: var(--color-bg-surface);
    border: 1px solid var(--color-border);
    border-radius: 6px;
  }

  .detail-panel h3 {
    margin-top: 0;
    font-size: 1.05rem;
  }

  @media (max-width: 640px) {
    .navbar {
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
      padding: 1rem;
    }

    .telemetry-bar {
      grid-template-columns: 1fr 1fr;
    }

    .articles-grid {
      grid-template-columns: 1fr;
    }
  }
</style>