<script>
  let activeTab = 'overview';
  let searchQuery = '';
  let statusFilter = 'all';

  function setTab(tab) {
    activeTab = tab;
  }
</script>

<main class="app-container">
  <header class="navbar">
    <div class="nav-brand">
      <span class="brand-logo" aria-hidden="true">◈</span>
      <span class="brand-title">Platform Console</span>
    </div>
    <nav class="nav-links" aria-label="Main Navigation">
      <button
        class="nav-link"
        class:active={activeTab === 'overview'}
        on:click={() => setTab('overview')}
        aria-current={activeTab === 'overview' ? 'page' : undefined}
      >
        Overview
      </button>
      <button
        class="nav-link"
        class:active={activeTab === 'activity'}
        on:click={() => setTab('activity')}
        aria-current={activeTab === 'activity' ? 'page' : undefined}
      >
        Activity
      </button>
      <button
        class="nav-link"
        class:active={activeTab === 'settings'}
        on:click={() => setTab('settings')}
        aria-current={activeTab === 'settings' ? 'page' : undefined}
      >
        Settings
      </button>
    </nav>
  </header>

  <section class="hero-section" aria-labelledby="hero-heading">
    <div class="hero-content">
      <h1 id="hero-heading" class="hero-title">Mission Operations & Workflows</h1>
      <p class="hero-subtitle">
        Streamlined execution tracking, real-time lifecycle monitoring, and governance controls across all environments.
      </p>
    </div>
  </section>

  <section class="controls-section" aria-label="Filter and Search Controls">
    <div class="search-box">
      <label for="search-input" class="sr-only">Search tasks and workflows</label>
      <input
        id="search-input"
        type="search"
        bind:value={searchQuery}
        placeholder="Search workflows, tasks, tags..."
        class="input-search"
      />
    </div>

    <div class="filter-controls">
      <label for="status-select" class="filter-label">Status:</label>
      <select id="status-select" bind:value={statusFilter} class="select-status">
        <option value="all">All States</option>
        <option value="active">Active</option>
        <option value="pending">Pending</option>
        <option value="completed">Completed</option>
      </select>
      <button type="button" class="btn-primary">
        New Execution
      </button>
    </div>
  </section>

  <section class="main-content" aria-label="Content Area">
    <div class="card-grid">
      <div class="status-card">
        <div class="card-header">
          <h2 class="card-title">Active Tasks</h2>
          <span class="badge badge-success">Healthy</span>
        </div>
        <p class="metric-value">24</p>
        <p class="metric-description">Operating within target SLA bounds</p>
      </div>

      <div class="status-card">
        <div class="card-header">
          <h2 class="card-title">Queue Latency</h2>
          <span class="badge badge-neutral">12ms</span>
        </div>
        <p class="metric-value">Normal</p>
        <p class="metric-description">Optimal dispatch distribution</p>
      </div>

      <div class="status-card">
        <div class="card-header">
          <h2 class="card-title">Completed Runs</h2>
          <span class="badge badge-neutral">24h</span>
        </div>
        <p class="metric-value">1,428</p>
        <p class="metric-description">Zero unhandled failure exceptions</p>
      </div>
    </div>
  </section>
</main>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #0f172a;
    color: #f8fafc;
    line-height: 1.5;
    overflow-x: hidden;
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

  .app-container {
    min-height: 100vh;
    max-width: 1440px;
    margin: 0 auto;
    padding: 0 1rem 3rem 1rem;
    box-sizing: border-box;
  }

  .navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid #1e293b;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .nav-brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .brand-logo {
    font-size: 1.5rem;
    color: #38bdf8;
  }

  .brand-title {
    font-size: 1.125rem;
    font-weight: 700;
    letter-spacing: -0.025em;
  }

  .nav-links {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .nav-link {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 0.95rem;
    font-weight: 500;
    padding: 0.5rem 0.875rem;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: color 0.15s ease, background-color 0.15s ease;
  }

  .nav-link:hover {
    color: #f8fafc;
    background-color: #1e293b;
  }

  .nav-link.active {
    color: #38bdf8;
    background-color: #0369a126;
  }

  .nav-link:focus-visible,
  .btn-primary:focus-visible,
  .input-search:focus-visible,
  .select-status:focus-visible {
    outline: 2px solid #38bdf8;
    outline-offset: 2px;
  }

  .hero-section {
    padding: 3rem 0 2rem 0;
  }

  .hero-title {
    font-size: 2rem;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.03em;
    line-height: 1.2;
  }

  .hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    max-width: 65ch;
    margin: 0;
  }

  .controls-section {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin: 1.5rem 0;
    flex-wrap: wrap;
    background: #1e293b50;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #334155;
  }

  .search-box {
    flex: 1 1 240px;
  }

  .input-search {
    width: 100%;
    padding: 0.625rem 0.875rem;
    background-color: #0f172a;
    border: 1px solid #475569;
    border-radius: 0.375rem;
    color: #f8fafc;
    font-size: 0.95rem;
  }

  .input-search::placeholder {
    color: #64748b;
  }

  .filter-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .filter-label {
    font-size: 0.875rem;
    color: #94a3b8;
  }

  .select-status {
    padding: 0.625rem 0.875rem;
    background-color: #0f172a;
    border: 1px solid #475569;
    border-radius: 0.375rem;
    color: #f8fafc;
    font-size: 0.95rem;
    cursor: pointer;
  }

  .btn-primary {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.625rem 1.25rem;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .btn-primary:hover {
    background-color: #0369a1;
  }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.25rem;
    margin-top: 1.5rem;
  }

  .status-card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 0.5rem;
    padding: 1.25rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #cbd5e1;
    margin: 0;
  }

  .badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 9999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-success {
    background-color: #065f46;
    color: #6ee7b7;
  }

  .badge-neutral {
    background-color: #334155;
    color: #cbd5e1;
  }

  .metric-value {
    font-size: 2.25rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0.25rem 0;
    line-height: 1.1;
  }

  .metric-description {
    font-size: 0.85rem;
    color: #94a3b8;
    margin: 0;
  }

  @media (max-width: 640px) {
    .hero-title {
      font-size: 1.5rem;
    }

    .navbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .filter-controls {
      width: 100%;
      justify-content: flex-start;
    }

    .btn-primary {
      width: 100%;
    }
  }
</style>
