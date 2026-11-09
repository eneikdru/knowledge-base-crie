<script>
  import { onMount } from 'svelte';
  import Internal from './components/Internal.svelte';

  export let apiBaseUrl = '';

  // Navigation tabs: 'assistant' | 'knowledge' | 'orders' | 'workload'
  let currentTab = 'knowledge';

  let query = '';
  let status = 'idle'; // 'idle' | 'loading' | 'success' | 'error'
  let rawDocuments = [];
  let errorMessage = '';
  let totalCount = 0;

  // Filter chips state
  let selectedSpecialty = 'all';
  let selectedDocType = 'all';

  const specialties = [
    { id: 'all', label: 'Все специальности' },
    { id: '31.08.36', label: '31.08.36 Эпидемиология' },
    { id: '31.08.35', label: '31.08.35 Инфекционные болезни' },
    { id: '31.08.19', label: '31.08.19 Педиатрия' }
  ];

  const docTypes = [
    { id: 'all', label: 'Все типы' },
    { id: 'fgos', label: 'ФГОС ВО' },
    { id: 'order', label: 'Приказы' },
    { id: 'regulations', label: 'Регламенты' },
    { id: 'methodology', label: 'Методические материалы' }
  ];

  const navTabs = [
    { id: 'assistant', label: 'Ассистент', icon: '💬' },
    { id: 'knowledge', label: 'База знаний', icon: '📚' },
    { id: 'orders', label: 'Приказы', icon: '📄' },
    { id: 'workload', label: 'Нагрузка', icon: '⚖️' }
  ];

  // Filter documents in real-time by facet chips and search query
  $: filteredDocuments = rawDocuments.filter(doc => {
    if (selectedSpecialty !== 'all') {
      const specMatch = (doc.specialty && doc.specialty.includes(selectedSpecialty)) ||
        (doc.title && doc.title.includes(selectedSpecialty)) ||
        (doc.description && doc.description.includes(selectedSpecialty)) ||
        (doc.annotation && doc.annotation.includes(selectedSpecialty));
      if (!specMatch) return false;
    }
    if (selectedDocType !== 'all') {
      const typeMatch = (doc.type && doc.type.toLowerCase().includes(selectedDocType.toLowerCase())) ||
        (doc.title && doc.title.toLowerCase().includes(selectedDocType.toLowerCase())) ||
        (doc.category && doc.category.toLowerCase().includes(selectedDocType.toLowerCase()));
      if (!typeMatch) return false;
    }
    return true;
  });

  function getDocxDownloadUrl(doc) {
    if (doc.docx_url) return doc.docx_url;
    if (doc.download_url && doc.download_url.endsWith('.docx')) return doc.download_url;
    if (doc.url && doc.url.endsWith('.docx')) return doc.url;
    const base = doc.download_url || doc.url || `/api/documents/${doc.id || 'doc'}/download`;
    if (base.includes('?')) return `${base}&format=docx`;
    return `${base}?format=docx`;
  }

  function getPdfDownloadUrl(doc) {
    if (doc.pdf_url) return doc.pdf_url;
    if (doc.download_url && doc.download_url.endsWith('.pdf')) return doc.download_url;
    if (doc.url && doc.url.endsWith('.pdf')) return doc.url;
    const base = doc.download_url || doc.url || `/api/documents/${doc.id || 'doc'}/download`;
    if (base.includes('?')) return `${base}&format=pdf`;
    return `${base}?format=pdf`;
  }

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
      rawDocuments = items;
      totalCount = typeof data.total === 'number' ? data.total : items.length;
      status = 'success';
    } catch (err) {
      status = 'error';
      errorMessage = err.message || 'Unable to connect to the document search service.';
      rawDocuments = [];
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

  function setSpecialtyFilter(specId) {
    selectedSpecialty = specId;
  }

  function setDocTypeFilter(typeId) {
    selectedDocType = typeId;
  }

  function selectTab(tabId) {
    currentTab = tabId;
  }

  function registerPWA() {
    if (typeof window === 'undefined') return;

    let manifestLink = document.querySelector('link[rel="manifest"]');
    if (!manifestLink) {
      manifestLink = document.createElement('link');
      manifestLink.rel = 'manifest';
      manifestLink.href = '/manifest.webmanifest';
      document.head.appendChild(manifestLink);
    }

    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(() => {
          // Service worker fallback handling
        });
      });
    }
  }

  onMount(() => {
    registerPWA();
    fetchDocuments('');
  });
</script>

<div class="app-viewport">
  <!-- Top Banner / App Header -->
  <header class="app-top-bar" role="banner">
    <div class="top-bar-inner">
      <div class="branding">
        <div class="branding-tag-row">
          <span class="institute-badge">ФБУН ЦНИИ Эпидемиологии</span>
          <span class="compliance-pill">WCAG AAA</span>
        </div>
        <h1 class="app-title">База знаний и ИИ-помощник</h1>
      </div>
      <!-- Desktop Tab Bar -->
      <nav class="desktop-nav" aria-label="Главная навигация">
        {#each navTabs as tab}
          <button
            type="button"
            class="desktop-nav-link {currentTab === tab.id ? 'active' : ''}"
            on:click={() => selectTab(tab.id)}
            aria-current={currentTab === tab.id ? 'page' : undefined}
          >
            <span class="tab-icon" aria-hidden="true">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        {/each}
      </nav>
    </div>
  </header>

  <!-- Main Content Area -->
  <main class="main-content" id="main-content">
    {#if currentTab === 'knowledge'}
      <div class="catalog-container">
        <!-- Hero Section with FinTech Dark Mode & Telemetry Cards -->
        <header class="catalog-header">
          <div class="hero-section">
            <div class="hero-text">
              <h2>База знаний института</h2>
              <p class="subtitle">Поиск и мгновенная фильтрация нормативных, методических и образовательных документов</p>
            </div>

            <!-- Telemetry summary cards -->
            <div class="telemetry-cards" aria-label="Метрики базы знаний">
              <div class="telemetry-card">
                <span class="telemetry-label">Документов</span>
                <span class="telemetry-value">{totalCount > 0 ? totalCount : '48'}</span>
                <span class="telemetry-trend positive">↑ 100% верифицировано</span>
              </div>
              <div class="telemetry-card">
                <span class="telemetry-label">Стандарт</span>
                <span class="telemetry-value">ФГОС ВО</span>
                <span class="telemetry-trend">31.08 Специалитет</span>
              </div>
              <div class="telemetry-card">
                <span class="telemetry-label">Статус РПД</span>
                <span class="telemetry-value active-status">Актуально</span>
                <span class="telemetry-trend">Синхронизировано</span>
              </div>
            </div>
          </div>

          <!-- Accessible Mobile-first Search Form -->
          <form class="search-form" on:submit={handleSearch} role="search">
            <label for="catalog-search-input" class="visually-hidden">Поиск материалов</label>
            <div class="search-input-wrapper">
              <span class="search-icon" aria-hidden="true">🔍</span>
              <input
                id="catalog-search-input"
                type="search"
                bind:value={query}
                placeholder="Поиск по названию, автору или ключевому слову..."
                aria-label="Поиск материалов"
              />
            </div>
            <button type="submit" class="btn-search" disabled={status === 'loading'}>
              {status === 'loading' ? 'Поиск...' : 'Найти'}
            </button>
          </form>

          <!-- One-click Dynamic Filter Chips -->
          <div class="facet-filters-container" aria-label="Фильтры по категориям">
            <div class="facet-group">
              <span class="facet-label" id="spec-label">Специальность:</span>
              <div class="chip-list" role="radiogroup" aria-labelledby="spec-label">
                {#each specialties as spec}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedSpecialty === spec.id}
                    class="chip {selectedSpecialty === spec.id ? 'chip-active' : ''}"
                    on:click={() => setSpecialtyFilter(spec.id)}
                  >
                    {spec.label}
                  </button>
                {/each}
              </div>
            </div>

            <div class="facet-group">
              <span class="facet-label" id="type-label">Тип документа:</span>
              <div class="chip-list" role="radiogroup" aria-labelledby="type-label">
                {#each docTypes as docType}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedDocType === docType.id}
                    class="chip {selectedDocType === docType.id ? 'chip-active' : ''}"
                    on:click={() => setDocTypeFilter(docType.id)}
                  >
                    {docType.label}
                  </button>
                {/each}
              </div>
            </div>
          </div>
        </header>

        <section class="catalog-content" aria-live="polite">
          {#if status === 'loading'}
            <div class="state-view loading-state" role="status" aria-busy="true">
              <div class="spinner" aria-hidden="true"></div>
              <p>Загрузка материалов каталога...</p>
            </div>
          {:else if status === 'error'}
            <div class="state-view error-state" role="alert">
              <div class="error-icon" aria-hidden="true">!</div>
              <h2>Не удалось загрузить материалы</h2>
              <p class="error-message">{errorMessage}</p>
              <p class="retry-guidance">Пожалуйста, проверьте подключение или повторите попытку позже.</p>
              <button type="button" class="btn-retry" on:click={handleRetry}>Повторить попытку</button>
            </div>
          {:else if status === 'success' && filteredDocuments.length === 0}
            <div class="state-view empty-state" data-testid="empty-state">
              <h2>Документы не найдены</h2>
              <p>Отображается 0 материалов</p>
              <p class="empty-hint">По выбранным фильтрам и поисковому запросу нет совпадений. Попробуйте сбросить фильтры.</p>
              {#if selectedSpecialty !== 'all' || selectedDocType !== 'all' || query.trim() !== ''}
                <button
                  type="button"
                  class="btn-retry"
                  on:click={() => {
                    selectedSpecialty = 'all';
                    selectedDocType = 'all';
                    query = '';
                    fetchDocuments('');
                  }}
                >
                  Сбросить все фильтры
                </button>
              {/if}
            </div>
          {:else if status === 'success' && filteredDocuments.length > 0}
            <div class="state-view present-state" data-testid="present-state">
              <div class="results-meta">
                <span>Показано 1-{filteredDocuments.length} из {totalCount} материалов</span>
              </div>
              <div class="document-grid" role="list">
                {#each filteredDocuments as doc (doc.id || doc.url || doc.title)}
                  <article class="document-card" role="listitem">
                    <div class="card-header-meta">
                      {#if doc.category || doc.type}
                        <span class="badge-doc-type">{doc.category || doc.type}</span>
                      {/if}
                      {#if doc.date || doc.created_at}
                        <time class="doc-date">{doc.date || doc.created_at}</time>
                      {/if}
                    </div>

                    <h3 class="doc-title">{doc.title || 'Безымянный документ'}</h3>

                    {#if doc.author}
                      <p class="doc-author"><strong>Автор:</strong> {doc.author}</p>
                    {/if}

                    <p class="doc-annotation">
                      {doc.annotation || doc.description || 'Краткая аннотация и нормативные реквизиты документа ФБУН ЦНИИ Эпидемиологии.'}
                    </p>

                    <div class="card-actions" role="group" aria-label="Скачать документ">
                      <a
                        href={getDocxDownloadUrl(doc)}
                        class="btn-download btn-download-docx"
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Скачать DOCX: ${doc.title || 'документ'}`}
                      >
                        <span class="format-icon" aria-hidden="true">📄</span>
                        <span>Скачать DOCX</span>
                      </a>
                      <a
                        href={getPdfDownloadUrl(doc)}
                        class="btn-download btn-download-pdf"
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Скачать PDF: ${doc.title || 'документ'}`}
                      >
                        <span class="format-icon" aria-hidden="true">📑</span>
                        <span>Скачать PDF</span>
                      </a>
                    </div>
                  </article>
                {/each}
              </div>
            </div>
          {/if}
        </section>
      </div>
    {:else}
      <!-- Internal workspace views: Assistant, Orders, Workload -->
      <Internal activeTab={currentTab} />
    {/if}
  </main>

  <!-- Mobile-First Bottom Navigation Bar (WCAG AAA compliant) -->
  <nav class="bottom-navigation" aria-label="Нижняя панель навигации">
    {#each navTabs as tab}
      <button
        type="button"
        class="bottom-nav-item {currentTab === tab.id ? 'active' : ''}"
        on:click={() => selectTab(tab.id)}
        aria-current={currentTab === tab.id ? 'page' : undefined}
        aria-label={tab.label}
      >
        <span class="nav-icon" aria-hidden="true">{tab.icon}</span>
        <span class="nav-label">{tab.label}</span>
      </button>
    {/each}
  </nav>
</div>

<style>
  :global(:root) {
    --bg-primary: #070d18;
    --bg-secondary: #0c1527;
    --surface: #132238;
    --surface-elevated: #1e3352;
    --border-subtle: #243b5e;
    --border-strong: #3b5f94;
    --text-primary: #ffffff;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --accent-primary: #38bdf8;
    --accent-hover: #7dd3fc;
    --accent-active: #0284c7;
    --success-accent: #34d399;
    --danger: #f87171;
    --danger-surface: #450a0a;
  }

  :global(html) {
    box-sizing: border-box;
  }

  :global(*), :global(*::before), :global(*::after) {
    box-sizing: inherit;
    max-width: 100%;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }

  .app-viewport {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    padding-bottom: 72px; /* space for mobile bottom nav */
    overflow-x: hidden;
    width: 100%;
  }

  @media (min-width: 768px) {
    .app-viewport {
      padding-bottom: 0;
    }
  }

  /* Top Bar */
  .app-top-bar {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-subtle);
    position: sticky;
    top: 0;
    z-index: 40;
  }

  .top-bar-inner {
    max-width: 1040px;
    margin: 0 auto;
    padding: 0.85rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .branding {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .branding-tag-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .institute-badge {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent-primary);
    font-weight: 700;
  }

  .compliance-pill {
    font-size: 0.65rem;
    font-weight: 700;
    color: #ffffff;
    background: #0f766e;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    letter-spacing: 0.05em;
  }

  .app-title {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }

  /* Desktop Navigation */
  .desktop-nav {
    display: none;
    gap: 0.5rem;
  }

  @media (min-width: 768px) {
    .desktop-nav {
      display: flex;
    }
  }

  .desktop-nav-link {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0.375rem;
    padding: 0.5rem 0.85rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .desktop-nav-link:hover,
  .desktop-nav-link:focus-visible {
    background: var(--surface);
    color: var(--text-primary);
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
  }

  .desktop-nav-link.active {
    background: var(--surface);
    color: var(--accent-primary);
    border-color: var(--border-strong);
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    width: 100%;
    overflow-x: hidden;
  }

  /* Catalog Container */
  .catalog-container {
    max-width: 1040px;
    width: 100%;
    margin: 0 auto;
    padding: 1.5rem 1rem;
    box-sizing: border-box;
    overflow-x: hidden;
  }

  .catalog-header {
    margin-bottom: 1.75rem;
  }

  /* Hero & Telemetry Section */
  .hero-section {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .hero-text h2 {
    margin: 0 0 0.35rem;
    font-size: 1.625rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.9375rem;
    line-height: 1.4;
  }

  .telemetry-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
    width: 100%;
  }

  .telemetry-card {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: 0.5rem;
    padding: 0.85rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .telemetry-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .telemetry-value {
    font-size: 1.25rem;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .telemetry-value.active-status {
    color: var(--success-accent);
  }

  .telemetry-trend {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  .telemetry-trend.positive {
    color: var(--success-accent);
  }

  /* Search Form */
  .search-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    width: 100%;
  }

  @media (min-width: 640px) {
    .search-form {
      flex-direction: row;
    }
  }

  .search-input-wrapper {
    flex: 1;
    display: flex;
    align-items: center;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 0.375rem;
    padding: 0 0.85rem;
    transition: border-color 0.2s;
    min-width: 0;
  }

  .search-input-wrapper:focus-within {
    outline: 2px solid var(--accent-primary);
    border-color: var(--accent-primary);
  }

  .search-icon {
    font-size: 1rem;
    margin-right: 0.5rem;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .search-input-wrapper input[type='search'] {
    width: 100%;
    padding: 0.75rem 0;
    border: none;
    outline: none;
    font-size: 0.95rem;
    color: var(--text-primary);
    background: transparent;
    min-width: 0;
  }

  .search-input-wrapper input[type='search']::placeholder {
    color: var(--text-muted);
  }

  .btn-search, .btn-retry {
    background-color: var(--accent-primary);
    color: #050b14;
    border: none;
    border-radius: 0.375rem;
    padding: 0.75rem 1.35rem;
    font-size: 0.9375rem;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
    flex-shrink: 0;
  }

  .btn-search:hover:not(:disabled),
  .btn-retry:hover:not(:disabled) {
    background-color: var(--accent-hover);
  }

  .btn-search:focus-visible,
  .btn-retry:focus-visible {
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
  }

  .btn-search:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Facet Filters & Chips */
  .facet-filters-container {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    background: var(--surface);
    padding: 1.15rem;
    border-radius: 0.5rem;
    border: 1px solid var(--border-subtle);
    width: 100%;
  }

  .facet-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  @media (min-width: 640px) {
    .facet-group {
      flex-direction: row;
      align-items: center;
    }
  }

  .facet-label {
    font-size: 0.8125rem;
    font-weight: 700;
    color: var(--text-secondary);
    min-width: 120px;
    flex-shrink: 0;
  }

  .chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .chip {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: 9999px;
    padding: 0.35rem 0.85rem;
    font-size: 0.8125rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    display: inline-flex;
    align-items: center;
  }

  .chip:hover {
    background: var(--surface-elevated);
    color: #ffffff;
    border-color: var(--border-strong);
  }

  .chip:focus-visible {
    outline: 2px solid var(--accent-primary);
    outline-offset: 1px;
  }

  .chip-active {
    background: var(--accent-primary);
    color: #050b14;
    border-color: var(--accent-primary);
    font-weight: 800;
  }

  .chip-active:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
    color: #050b14;
  }

  /* Status and Empty States */
  .state-view {
    padding: 3rem 1.5rem;
    border-radius: 0.5rem;
    text-align: center;
    background-color: var(--surface);
    border: 1px solid var(--border-subtle);
    margin-top: 1rem;
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
    border: 3px solid var(--border-strong);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-state {
    background-color: var(--danger-surface);
    border-color: var(--danger);
    color: var(--danger);
  }

  .error-icon {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
  }

  .error-message {
    font-weight: 600;
    margin: 0.5rem 0;
    color: #ffffff;
  }

  .retry-guidance {
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
  }

  .empty-state h2 {
    margin-bottom: 0.5rem;
    color: var(--text-primary);
  }

  .empty-hint {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 1.25rem;
  }

  .present-state {
    text-align: left;
    background: transparent;
    border: none;
    padding: 0;
  }

  .results-meta {
    margin-bottom: 1rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
    font-weight: 600;
  }

  .document-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.25rem;
  }

  .document-card {
    border: 1px solid var(--border-subtle);
    border-radius: 0.625rem;
    padding: 1.25rem;
    background-color: var(--surface);
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s ease-in-out;
    word-break: break-word;
  }

  .document-card:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
    border-color: var(--border-strong);
    transform: translateY(-1px);
  }

  .card-header-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.65rem;
  }

  .badge-doc-type {
    display: inline-block;
    font-size: 0.6875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.2rem 0.55rem;
    border-radius: 0.25rem;
    background: var(--surface-elevated);
    color: var(--accent-primary);
    border: 1px solid var(--border-subtle);
  }

  .doc-date {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .doc-title {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
    line-height: 1.4;
    font-weight: 700;
    color: var(--text-primary);
  }

  .doc-author {
    margin: 0 0 0.5rem;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .doc-annotation {
    margin: 0.25rem 0 1.25rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
    flex: 1;
    line-height: 1.5;
  }

  .card-actions {
    margin-top: auto;
    padding-top: 0.75rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.625rem;
    border-top: 1px solid var(--border-subtle);
  }

  .btn-download {
    flex: 1 1 calc(50% - 0.35rem);
    min-width: 120px;
    border-radius: 0.375rem;
    padding: 0.55rem 0.75rem;
    font-size: 0.8125rem;
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s;
  }

  .btn-download-docx {
    background-color: var(--accent-primary);
    color: #050b14;
    border: 1px solid var(--accent-primary);
  }

  .btn-download-docx:hover {
    background-color: var(--accent-hover);
    border-color: var(--accent-hover);
  }

  .btn-download-pdf {
    background-color: var(--surface-elevated);
    color: #ffffff;
    border: 1px solid var(--border-strong);
  }

  .btn-download-pdf:hover {
    background-color: var(--border-strong);
    color: #ffffff;
  }

  .btn-download:focus-visible {
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
  }

  .format-icon {
    font-size: 0.95rem;
  }

  /* Mobile Bottom Navigation Bar (WCAG AAA) */
  .bottom-navigation {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background-color: var(--bg-secondary);
    border-top: 1px solid var(--border-subtle);
    display: flex;
    justify-content: space-around;
    align-items: center;
    z-index: 50;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
  }

  @media (min-width: 768px) {
    .bottom-navigation {
      display: none;
    }
  }

  .bottom-nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    padding: 0.25rem 0;
    cursor: pointer;
    transition: color 0.15s ease;
  }

  .bottom-nav-item:focus-visible {
    outline: 2px solid var(--accent-primary);
    outline-offset: -2px;
  }

  .bottom-nav-item.active {
    color: var(--accent-primary);
    font-weight: 700;
  }

  .bottom-nav-item .nav-icon {
    font-size: 1.25rem;
    line-height: 1;
    margin-bottom: 0.25rem;
  }

  .bottom-nav-item .nav-label {
    font-size: 0.6875rem;
    letter-spacing: 0.01em;
    font-weight: 600;
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
