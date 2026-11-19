<script>
  import { onMount } from 'svelte';

  let query = '';
  let isLoading = false;
  let selectedFilter = 'all';
  let copiedPath = '';
  let copyTimeoutId = null;
  let errorMessage = '';

  const filterOptions = [
    { id: 'all', label: 'Все документы' },
    { id: 'regulations', label: 'Регламенты ординатуры' },
    { id: 'orders', label: 'Приказы' },
    { id: 'attestation', label: 'Аттестация' },
    { id: 'workload', label: 'Нагрузка ППС' }
  ];

  let messages = [
    {
      id: 1,
      role: 'assistant',
      text: 'Здравствуйте! Я ассистент по нормативному корпусу документов. Задайте вопрос или выберите категорию фильтра.',
      sources: []
    }
  ];

  async function submitQuery() {
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;

    const userMsgId = Date.now();
    messages = [
      ...messages,
      { id: userMsgId, role: 'user', text: trimmed, sources: [] }
    ];

    query = '';
    isLoading = true;
    errorMessage = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: trimmed,
          filter: selectedFilter
        })
      });

      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`);
      }

      const data = await response.json();
      const assistantResponseText = data.answer || data.response || 'Ответ сформирован по найденным источникам.';
      const assistantSources = Array.isArray(data.sources) ? data.sources : [];

      messages = [
        ...messages,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: assistantResponseText,
          sources: assistantSources
        }
      ];
    } catch (err) {
      errorMessage = err.message || 'Не удалось получить ответ от ассистента.';
      messages = [
        ...messages,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: 'Произошла ошибка при обращении к нормативному корпусу. Пожалуйста, повторите попытку.',
          sources: []
        }
      ];
    } finally {
      isLoading = false;
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitQuery();
    }
  }

  function setFilter(filterId) {
    selectedFilter = filterId;
  }

  async function copyPath(path) {
    if (!path) return;
    try {
      if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(path);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = path;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      copiedPath = path;
      if (copyTimeoutId) clearTimeout(copyTimeoutId);
      copyTimeoutId = setTimeout(() => {
        copiedPath = '';
      }, 2000);
    } catch (e) {
      console.error('Failed to copy document path', e);
    }
  }
</script>

<section class="assistant-board-container" aria-label="Нормативный ассистент">
  <header class="assistant-header">
    <h2>Нормативный ассистент</h2>
    <p class="subtitle">Семантический поиск по 1697 нормативным актам и регламентам</p>
  </header>

  <!-- Clickable filter chips -->
  <nav class="filter-chips-bar" aria-label="Фильтры документов">
    {#each filterOptions as filter}
      <button
        type="button"
        class="chip-btn"
        class:active={selectedFilter === filter.id}
        aria-pressed={selectedFilter === filter.id}
        on:click={() => setFilter(filter.id)}
      >
        {filter.label}
      </button>
    {/each}
  </nav>

  <!-- Chat messages area -->
  <div class="chat-history" role="log" aria-live="polite">
    {#each messages as msg (msg.id)}
      <article class="chat-message {msg.role}">
        <div class="message-bubble">
          <p class="message-text">{msg.text}</p>

          {#if msg.sources && msg.sources.length > 0}
            <div class="source-citations" aria-label="Источники цитирования">
              <span class="sources-title">Источники:</span>
              <div class="chips-list">
                {#each msg.sources as src}
                  <div class="citation-item">
                    <span class="source-chip" title={src.title || src.path}>
                      {src.title || src.name || src.path}
                    </span>
                    <button
                      type="button"
                      class="copy-path-btn"
                      title="Скопировать путь к документу"
                      aria-label="Скопировать путь к документу"
                      on:click={() => copyPath(src.path || src.file || src.title)}
                    >
                      {#if copiedPath === (src.path || src.file || src.title)}
                        <span class="copied-label">Скопировано</span>
                      {:else}
                        <span>Копировать путь</span>
                      {/if}
                    </button>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </article>
    {/each}

    {#if isLoading}
      <div class="loading-indicator" aria-live="assertive" aria-label="Загрузка ответа">
        <div class="spinner" aria-hidden="true"></div>
        <span>Поиск по нормативному корпусу...</span>
      </div>
    {/if}
  </div>

  <!-- Input bar -->
  <form class="assistant-input-form" on:submit|preventDefault={submitQuery}>
    <div class="input-wrapper">
      <input
        type="text"
        class="query-input"
        placeholder="Задайте вопрос по регламентам, приказам, аттестации..."
        bind:value={query}
        on:keydown={handleKeyDown}
        disabled={isLoading}
        aria-label="Запрос к нормативному ассистенту"
      />
      <button
        type="submit"
        class="submit-btn"
        disabled={isLoading || !query.trim()}
        aria-label="Отправить вопрос"
      >
        {#if isLoading}
          <span>Отправка...</span>
        {:else}
          <span>Отправить</span>
        {/if}
      </button>
    </div>
    {#if errorMessage}
      <div class="error-banner" role="alert">{errorMessage}</div>
    {/if}
  </form>
</section>

<style>
  .assistant-board-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 960px;
    margin: 0 auto;
    padding: 1rem;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1a202c;
  }

  .assistant-header {
    margin-bottom: 0.75rem;
  }

  .assistant-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: #2b6cb0;
  }

  .subtitle {
    margin: 0.25rem 0 0 0;
    font-size: 0.875rem;
    color: #718096;
  }

  .filter-chips-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .chip-btn {
    background: #edf2f7;
    border: 1px solid #cbd5e0;
    color: #4a5568;
    border-radius: 9999px;
    padding: 0.375rem 0.875rem;
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background-color 0.2s, border-color 0.2s, color 0.2s;
  }

  .chip-btn:hover {
    background: #e2e8f0;
  }

  .chip-btn.active {
    background: #3182ce;
    border-color: #2b6cb0;
    color: #ffffff;
    font-weight: 600;
  }

  .chip-btn:focus-visible {
    outline: 2px solid #3182ce;
    outline-offset: 2px;
  }

  .chat-history {
    flex: 1 1 auto;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.75rem;
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    min-height: 280px;
    margin-bottom: 1rem;
  }

  .chat-message {
    display: flex;
    width: 100%;
  }

  .chat-message.user {
    justify-content: flex-end;
  }

  .chat-message.assistant {
    justify-content: flex-start;
  }

  .message-bubble {
    max-width: 85%;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    line-height: 1.5;
    font-size: 0.9375rem;
    word-break: break-word;
  }

  .chat-message.user .message-bubble {
    background: #3182ce;
    color: #ffffff;
    border-bottom-right-radius: 2px;
  }

  .chat-message.assistant .message-bubble {
    background: #ffffff;
    color: #2d3748;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    border-bottom-left-radius: 2px;
  }

  .message-text {
    margin: 0;
    white-space: pre-wrap;
  }

  .source-citations {
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px dashed #e2e8f0;
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .sources-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .chips-list {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .citation-item {
    display: inline-flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    background: #edf2f7;
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.8125rem;
  }

  .source-chip {
    color: #2d3748;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 320px;
  }

  .copy-path-btn {
    background: #ffffff;
    border: 1px solid #cbd5e0;
    color: #4a5568;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    flex-shrink: 0;
    transition: background-color 0.2s;
  }

  .copy-path-btn:hover {
    background: #edf2f7;
  }

  .copy-path-btn:focus-visible {
    outline: 2px solid #3182ce;
    outline-offset: 1px;
  }

  .copied-label {
    color: #38a169;
    font-weight: 600;
  }

  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #718096;
    font-size: 0.875rem;
    padding: 0.5rem 0.25rem;
  }

  .spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid #cbd5e0;
    border-top-color: #3182ce;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .assistant-input-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .input-wrapper {
    display: flex;
    gap: 0.5rem;
  }

  .query-input {
    flex: 1 1 auto;
    padding: 0.625rem 0.875rem;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    font-size: 0.9375rem;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .query-input:focus {
    border-color: #3182ce;
    box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.15);
  }

  .submit-btn {
    padding: 0.625rem 1.25rem;
    background: #3182ce;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
    flex-shrink: 0;
  }

  .submit-btn:hover:not(:disabled) {
    background: #2b6cb0;
  }

  .submit-btn:focus-visible {
    outline: 2px solid #2b6cb0;
    outline-offset: 2px;
  }

  .submit-btn:disabled {
    background: #a0aec0;
    cursor: not-allowed;
  }

  .error-banner {
    color: #e53e3e;
    font-size: 0.8125rem;
  }

  @media (max-width: 640px) {
    .assistant-board-container {
      padding: 0.5rem;
    }
    .message-bubble {
      max-width: 95%;
    }
    .source-chip {
      max-width: 180px;
    }
  }
</style>
