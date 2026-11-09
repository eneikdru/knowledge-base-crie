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
        (doc.description && doc.description.includes(selectedSpecialty));
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

  // Setup PWA Manifest and Service Worker registration
  function registerPWA() {
    if (typeof window === 'undefined') return;

    // Ensure manifest link exists
    let manifestLink = document.querySelector('link[rel="manifest"]');
    if (!manifestLink) {
      manifestLink = document.createElement('link');
      manifestLink.rel = 'manifest';
      manifestLink.href = '/manifest.webmanifest';
      document.head.appendChild(manifestLink);
    }

    // Register Service Worker if supported
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
        <span class="institute-badge">ФБУН ЦНИИ Эпидемиологии</span>
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
        <header class="catalog-header">
          <h2>База знаний института</h2>
          <p class="subtitle">Поиск и мгновенная фильтрация нормативных, методических и образовательных документов</p>

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
                    <h3 class="doc-title">{doc.title || 'Безымянный документ'}</h3>
                    {#if doc.author}
                      <p class="doc-author"><strong>Автор:</strong> {doc.author}</p>
                    {/if}
                    {#if doc.date || doc.created_at}
                      <p class="doc-date"><strong>Дата:</strong> {doc.date || doc.created_at}</p>
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
                          Скачать документ
                        </a>
                      {/if}
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

  <!-- Mobile-First Bottom Navigation Bar (WCAG 2.1 AA compliant) -->
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
  :global(body) {
    margin: 0;
    padding: 0;
    background-color: #f8fafc;
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }

  .app-viewport {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    padding-bottom: 72px; /* space for mobile bottom nav */
  }

  @media (min-width: 768px) {
    .app-viewport {
      padding-bottom: 0;
    }
  }

  /* Top Bar */
  .app-top-bar {
    background: #0369a1;
    color: #ffffff;
    border-bottom: 2px solid #075985;
    position: sticky;
    top: 0;
    z-index: 40;
  }

  .top-bar-inner {
    max-width: 1040px;
    margin: 0 auto;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .branding {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .institute-badge {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #bae6fd;
    font-weight: 600;
  }

  .app-title {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0;
    color: #ffffff;
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
    gap: 0.35rem;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0.375rem;
    padding: 0.5rem 0.75rem;
    color: #f0f9ff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .desktop-nav-link:hover,
  .desktop-nav-link:focus-visible {
    background: rgba(255, 255, 255, 0.15);
    outline: 2px solid #ffffff;
    outline-offset: 2px;
  }

  .desktop-nav-link.active {
    background: #ffffff;
    color: #0369a1;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  /* Catalog Container */
  .catalog-container {
    max-width: 1040px;
    width: 100%;
    margin: 0 auto;
    padding: 1.5rem 1rem;
    box-sizing: border-box;
  }

  .catalog-header {
    margin-bottom: 1.5rem;
  }

  .catalog-header h2 {
    margin: 0 0 0.25rem;
    font-size: 1.5rem;
    font-weight: 700;
    color: #0f172a;
  }

  .subtitle {
    margin: 0 0 1.25rem;
    color: #475569;
    font-size: 0.9375rem;
  }

  .search-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
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
    background: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 0.375rem;
    padding: 0 0.75rem;
  }

  .search-input-wrapper:focus-within {
    outline: 2px solid #0369a1;
    border-color: #0369a1;
  }

  .search-icon {
    font-size: 1rem;
    margin-right: 0.5rem;
    color: #64748b;
  }

  .search-input-wrapper input[type='search'] {
    width: 100%;
    padding: 0.75rem 0;
    border: none;
    outline: none;
    font-size: 0.95rem;
    color: #0f172a;
    background: transparent;
  }

  .btn-search, .btn-retry, .btn-download {
    background-color: #0369a1;
    color: #ffffff;
    border: none;
    border-radius: 0.375rem;
    padding: 0.75rem 1.25rem;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
  }

  .btn-search:hover:not(:disabled),
  .btn-retry:hover:not(:disabled),
  .btn-download:hover:not(:disabled) {
    background-color: #075985;
  }

  .btn-search:focus-visible,
  .btn-retry:focus-visible,
  .btn-download:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: 2px;
  }

  .btn-search:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Facet Filters & Chips */
  .facet-filters-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    background: #f1f5f9;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #cbd5e1;
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
    color: #334155;
    min-width: 120px;
  }

  .chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
  }

  .chip {
    background: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 9999px;
    padding: 0.35rem 0.75rem;
    font-size: 0.8125rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    display: inline-flex;
    align-items: center;
  }

  .chip:hover {
    background: #e2e8f0;
    border-color: #94a3b8;
  }

  .chip:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: 1px;
  }

  .chip-active {
    background: #0369a1;
    color: #ffffff;
    border-color: #0369a1;
    font-weight: 600;
  }

  .chip-active:hover {
    background: #075985;
    border-color: #075985;
  }

  /* Status and Empty States */
  .state-view {
    padding: 3rem 1.5rem;
    border-radius: 0.5rem;
    text-align: center;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
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
    border: 3px solid #e2e8f0;
    border-top-color: #0369a1;
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
    color: #475569;
    font-weight: 500;
  }

  .document-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.25rem;
  }

  .document-card {
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    padding: 1.25rem;
    background-color: #ffffff;
    display: flex;
    flex-direction: column;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    transition: box-shadow 0.2s;
  }

  .document-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .doc-title {
    margin: 0 0 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: #0f172a;
  }

  .doc-author, .doc-date {
    margin: 0.25rem 0;
    font-size: 0.875rem;
    color: #475569;
  }

  .doc-description {
    margin: 0.75rem 0 1rem;
    font-size: 0.875rem;
    color: #64748b;
    flex: 1;
    line-height: 1.4;
  }

  .card-actions {
    margin-top: auto;
    padding-top: 0.5rem;
  }

  /* Mobile Bottom Navigation Bar (WCAG 2.1 AA) */
  .bottom-navigation {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 64px;
    background-color: #ffffff;
    border-top: 1px solid #cbd5e1;
    display: flex;
    justify-content: space-around;
    align-items: center;
    z-index: 50;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.06);
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
    color: #475569;
    padding: 0.25rem 0;
    cursor: pointer;
    transition: color 0.15s ease;
  }

  .bottom-nav-item:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: -2px;
  }

  .bottom-nav-item.active {
    color: #0369a1;
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
