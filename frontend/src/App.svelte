<script>
  import { onMount } from 'svelte';

  let searchQuery = '';
  let selectedSpecialty = '';
  let selectedCategory = '';
  let searchResults = [];
  let facets = { specialties: [], categories: [] };
  let loading = false;
  let error = null;

  const institutionalStats = {
    departments: 12,
    ordinators: 148,
    aspirators: 64,
    normativeDocuments: 520
  };

  const currentUser = {
    name: 'Научный сотрудник',
    email: 'academic@crie.ru',
    role: 'FBUN CRIE Academic Registry'
  };

  async function fetchFacets() {
    try {
      const res = await fetch('/api/documents/facets');
      if (res.ok) {
        facets = await res.json();
      } else {
        facets = {
          specialties: ['Эпидемиология', 'Инфекционные болезни', 'Микробиология', 'Вирусология'],
          categories: ['Учебные планы', 'Нормативные акты', 'Методические материалы', 'Приказы']
        };
      }
    } catch (e) {
      facets = {
        specialties: ['Эпидемиология', 'Инфекционные болезни', 'Микробиология', 'Вирусология'],
        categories: ['Учебные планы', 'Нормативные акты', 'Методические материалы', 'Приказы']
      };
    }
  }

  async function handleSearch(event) {
    if (event) event.preventDefault();
    loading = true;
    error = null;

    const params = new URLSearchParams();
    if (searchQuery) params.append('q', searchQuery);
    if (selectedSpecialty) params.append('specialty', selectedSpecialty);
    if (selectedCategory) params.append('category', selectedCategory);

    try {
      const res = await fetch(`/api/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Ошибка загрузки: ${res.status}`);
      }
      const data = await res.json();
      searchResults = Array.isArray(data) ? data : (data.items || []);
    } catch (err) {
      error = err.message;
      searchResults = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchFacets();
    handleSearch();
  });
</script>

<main class="crie-portal">
  <header class="portal-header">
    <div class="brand-block">
      <div class="emblem">ФБУН ЦНИИ Эпидемиологии</div>
      <div class="sub-brand">Образовательный портал: Ординатура и Аспирантура</div>
    </div>
    <div class="user-profile">
      <span class="user-name">{currentUser.name}</span>
      <span class="user-email">{currentUser.email}</span>
      <span class="badge-role">{currentUser.role}</span>
    </div>
  </header>

  <section class="metrics-bar">
    <div class="metric-card">
      <div class="metric-value">{institutionalStats.departments}</div>
      <div class="metric-label">Кафедры и отделы</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{institutionalStats.ordinators}</div>
      <div class="metric-label">Ординаторы</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{institutionalStats.aspirators}</div>
      <div class="metric-label">Аспиранты</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{institutionalStats.normativeDocuments}</div>
      <div class="metric-label">Нормативные документы</div>
    </div>
  </section>

  <section class="search-section">
    <form on:submit={handleSearch} class="crie-form">
      <div class="form-group search-input-group">
        <label for="search-query">Поиск по каталогу нормативных актов и программ</label>
        <input
          id="search-query"
          type="text"
          bind:value={searchQuery}
          placeholder="Введите наименование документа, регламента или специальности..."
        />
      </div>

      <div class="filter-row">
        <div class="form-group">
          <label for="specialty-filter">Специальность ординатуры/аспирантуры</label>
          <select id="specialty-filter" bind:value={selectedSpecialty} on:change={handleSearch}>
            <option value="">Все специальности</option>
            {#each facets.specialties as item}
              <option value={item}>{item}</option>
            {/each}
          </select>
        </div>

        <div class="form-group">
          <label for="category-filter">Категория документации</label>
          <select id="category-filter" bind:value={selectedCategory} on:change={handleSearch}>
            <option value="">Все категории</option>
            {#each facets.categories as item}
              <option value={item}>{item}</option>
            {/each}
          </select>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn-submit" disabled={loading}>
            {loading ? 'Поиск...' : 'Найти'}
          </button>
        </div>
      </div>
    </form>
  </section>

  <section class="results-section">
    {#if loading}
      <div class="status-state">Загрузка реестра документов ФБУН ЦНИИЭ...</div>
    {:else if error}
      <div class="status-state error">{error}</div>
    {:else if searchResults.length === 0}
      <div class="status-state">Документы и учебные материалы не найдены по заданным критериям.</div>
    {:else}
      <div class="documents-grid">
        {#each searchResults as doc (doc.id || doc.title)}
          <article class="document-card">
            <h3>{doc.title || 'Нормативный акт института'}</h3>
            <p class="doc-meta">
              <span class="badge">{doc.specialty || 'Общая специальность'}</span>
              <span class="badge category">{doc.category || 'Регламент'}</span>
            </p>
            {#if doc.description}
              <p class="doc-desc">{doc.description}</p>
            {/if}
            {#if doc.date}
              <span class="doc-date">Утверждено: {doc.date}</span>
            {/if}
          </article>
        {/each}
      </div>
    {/if}
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: #f7fafc;
    color: #1a202c;
  }

  .crie-portal {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
  }

  .portal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #ffffff;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
  }

  .emblem {
    font-size: 1.25rem;
    font-weight: 700;
    color: #2b6cb0;
  }

  .sub-brand {
    font-size: 0.875rem;
    color: #718096;
  }

  .user-profile {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
  }

  .user-name {
    font-weight: 600;
    font-size: 0.95rem;
  }

  .user-email {
    font-size: 0.8rem;
    color: #718096;
  }

  .badge-role {
    font-size: 0.75rem;
    background: #ebf8ff;
    color: #2b6cb0;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
  }

  .metrics-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .metric-card {
    background: #ffffff;
    padding: 1.25rem;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    border-left: 4px solid #3182ce;
  }

  .metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #2d3748;
  }

  .metric-label {
    font-size: 0.85rem;
    color: #718096;
    margin-top: 0.25rem;
  }

  .search-section {
    background: #ffffff;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
  }

  .crie-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    flex: 1;
  }

  .form-group label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #4a5568;
  }

  .form-group input,
  .form-group select {
    padding: 0.6rem 0.75rem;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    font-size: 0.95rem;
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
  }

  .form-actions {
    display: flex;
    align-items: flex-end;
  }

  .btn-submit {
    background: #3182ce;
    color: #ffffff;
    border: none;
    padding: 0.65rem 1.5rem;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    height: 42px;
  }

  .btn-submit:hover {
    background: #2b6cb0;
  }

  .btn-submit:disabled {
    background: #a0aec0;
    cursor: not-allowed;
  }

  .status-state {
    text-align: center;
    padding: 2rem;
    background: #ffffff;
    border-radius: 8px;
    color: #718096;
  }

  .status-state.error {
    color: #e53e3e;
  }

  .documents-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
  }

  .document-card {
    background: #ffffff;
    padding: 1.25rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .document-card h3 {
    margin: 0;
    font-size: 1.05rem;
    color: #2d3748;
  }

  .doc-meta {
    display: flex;
    gap: 0.5rem;
    margin: 0;
  }

  .badge {
    font-size: 0.75rem;
    background: #edf2f7;
    color: #4a5568;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
  }

  .badge.category {
    background: #e2e8f0;
    color: #2d3748;
  }

  .doc-desc {
    font-size: 0.875rem;
    color: #4a5568;
    margin: 0;
    line-height: 1.4;
  }

  .doc-date {
    font-size: 0.75rem;
    color: #a0aec0;
    margin-top: auto;
  }
</style>