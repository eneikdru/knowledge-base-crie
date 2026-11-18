<script>
  let searchQuery = '';
  let isSearching = false;
  let activeCategory = 'all';
  let results = [
    {
      id: 1,
      title: 'Getting Started with the Knowledge Base',
      category: 'guide',
      snippet: 'Learn how to navigate, search, and contribute documentation across your team workspaces.',
      updatedAt: '2026-11-15'
    },
    {
      id: 2,
      title: 'Design System Guidelines & Visual Tokens',
      category: 'design',
      snippet: 'Detailed specification for color tokens, typography scales, spacing units, and responsive breakpoints.',
      updatedAt: '2026-11-17'
    },
    {
      id: 3,
      title: 'API Integration & Service Endpoints',
      category: 'api',
      snippet: 'Comprehensive reference of REST endpoints, authentication protocols, and error response schemas.',
      updatedAt: '2026-11-18'
    }
  ];

  const categories = [
    { id: 'all', label: 'All Resources' },
    { id: 'guide', label: 'Guides' },
    { id: 'design', label: 'Design' },
    { id: 'api', label: 'API Reference' }
  ];

  function handleSearch(event) {
    if (event) event.preventDefault();
    isSearching = true;
    setTimeout(() => {
      isSearching = false;
    }, 200);
  }

  function setCategory(id) {
    activeCategory = id;
  }

  $: filteredResults = results.filter((item) => {
    const matchesCategory = activeCategory === 'all' || item.category === activeCategory;
    const query = searchQuery.trim().toLowerCase();
    const matchesQuery = !query || item.title.toLowerCase().includes(query) || item.snippet.toLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });
</script>

<main class="app-container">
  <header class="hero-section">
    <div class="hero-content">
      <span class="badge">Documentation & Specs</span>
      <h1 class="hero-title">Knowledge Base</h1>
      <p class="hero-subtitle">
        Search through architecture notes, design guidelines, and API references.
      </p>

      <form class="search-box" on:submit|preventDefault={handleSearch} role="search">
        <div class="input-wrapper">
          <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
          </svg>
          <input
            type="search"
            bind:value={searchQuery}
            placeholder="Search documentation, specs, guides..."
            aria-label="Search knowledge base"
            class="search-input"
          />
          {#if searchQuery}
            <button
              type="button"
              class="clear-btn"
              aria-label="Clear search query"
              on:click={() => (searchQuery = '')}
            >
              ✕
            </button>
          {/if}
        </div>
        <button type="submit" class="search-submit-btn" disabled={isSearching}>
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </form>

      <div class="category-filters" role="tablist" aria-label="Filter by category">
        {#each categories as cat}
          <button
            type="button"
            role="tab"
            aria-selected={activeCategory === cat.id}
            class="filter-pill {activeCategory === cat.id ? 'active' : ''}"
            on:click={() => setCategory(cat.id)}
          >
            {cat.label}
          </button>
        {/each}
      </div>
    </div>
  </header>

  <section class="results-section" aria-live="polite">
    <div class="results-header">
      <h2 class="results-count">
        {filteredResults.length} {filteredResults.length === 1 ? 'result' : 'results'} found
      </h2>
    </div>

    {#if filteredResults.length > 0}
      <div class="cards-grid">
        {#each filteredResults as item (item.id)}
          <article class="result-card">
            <div class="card-meta">
              <span class="category-tag {item.category}">{item.category.toUpperCase()}</span>
              <time datetime={item.updatedAt} class="card-date">{item.updatedAt}</time>
            </div>
            <h3 class="card-title">{item.title}</h3>
            <p class="card-snippet">{item.snippet}</p>
            <a href="#" class="card-link" on:click|preventDefault>View document &rarr;</a>
          </article>
        {/each}
      </div>
    {:else}
      <div class="empty-state">
        <p class="empty-title">No matching documents found</p>
        <p class="empty-desc">Try adjusting your query or selecting a different category filter.</p>
      </div>
    {/if}
  </section>
</main>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #f8fafc;
    color: #0f172a;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }

  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: 100%;
  }

  .hero-section {
    background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
    border-bottom: 1px solid #e2e8f0;
    padding: 3rem 1.25rem 2.5rem;
    display: flex;
    justify-content: center;
    width: 100%;
  }

  .hero-content {
    width: 100%;
    max-width: 800px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 0.25rem 0.75rem;
    background-color: #e0e7ff;
    color: #4338ca;
    border-radius: 9999px;
    margin-bottom: 1rem;
  }

  .hero-title {
    font-size: 2.25rem;
    line-height: 1.2;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.75rem;
  }

  .hero-subtitle {
    font-size: 1.05rem;
    line-height: 1.5;
    color: #475569;
    max-width: 600px;
    margin: 0 0 2rem;
  }

  .search-box {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  @media (min-width: 640px) {
    .search-box {
      flex-direction: row;
    }
  }

  .input-wrapper {
    position: relative;
    flex: 1;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 1rem;
    width: 1.25rem;
    height: 1.25rem;
    color: #94a3b8;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 0.85rem 2.5rem 0.85rem 2.75rem;
    font-size: 1rem;
    color: #0f172a;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    outline: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .search-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
  }

  .clear-btn {
    position: absolute;
    right: 0.75rem;
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 0.875rem;
    cursor: pointer;
    padding: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .clear-btn:hover {
    color: #475569;
  }

  .search-submit-btn {
    padding: 0.85rem 1.5rem;
    font-size: 1rem;
    font-weight: 600;
    color: #ffffff;
    background-color: #2563eb;
    border: none;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
    white-space: nowrap;
  }

  .search-submit-btn:hover:not(:disabled) {
    background-color: #1d4ed8;
  }

  .search-submit-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .category-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
  }

  .filter-pill {
    padding: 0.4rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #475569;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 9999px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .filter-pill:hover {
    background-color: #f8fafc;
    color: #1e293b;
  }

  .filter-pill.active {
    background-color: #0f172a;
    color: #ffffff;
    border-color: #0f172a;
  }

  .results-section {
    flex: 1;
    width: 100%;
    max-width: 1080px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
  }

  .results-header {
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .results-count {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin: 0;
  }

  .cards-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
  }

  @media (min-width: 640px) {
    .cards-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (min-width: 1024px) {
    .cards-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  .result-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  }

  .result-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
    border-color: #cbd5e1;
  }

  .card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .category-tag {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 0.25rem;
    background-color: #f1f5f9;
    color: #475569;
  }

  .category-tag.guide {
    background-color: #e0e7ff;
    color: #4338ca;
  }

  .category-tag.design {
    background-color: #fae8ff;
    color: #86198f;
  }

  .category-tag.api {
    background-color: #dbeafe;
    color: #1e40af;
  }

  .card-date {
    font-size: 0.75rem;
    color: #94a3b8;
  }

  .card-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0 0 0.5rem;
    line-height: 1.35;
  }

  .card-snippet {
    font-size: 0.9rem;
    line-height: 1.5;
    color: #64748b;
    margin: 0 0 1.25rem;
    flex: 1;
  }

  .card-link {
    font-size: 0.875rem;
    font-weight: 600;
    color: #2563eb;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .card-link:hover {
    text-decoration: underline;
  }

  .empty-state {
    text-align: center;
    padding: 4rem 1.5rem;
    background-color: #ffffff;
    border: 1px dashed #cbd5e1;
    border-radius: 0.75rem;
  }

  .empty-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #334155;
    margin: 0 0 0.5rem;
  }

  .empty-desc {
    font-size: 0.9rem;
    color: #64748b;
    margin: 0;
  }
</style>
