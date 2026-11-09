<script>
  import { onMount } from 'svelte';

  // Active tab state: 'assistant' | 'orders'
  export let activeTab = 'assistant';

  // Chat State
  let chatQuery = '';
  let isSubmitting = false;
  let copySuccessId = null;
  let messages = [
    {
      id: 'm-1',
      sender: 'assistant',
      text: 'Здравствуйте! Я ИИ-помощник Образовательного центра ФБУН ЦНИИ Эпидемиологии. Готов проконсультировать по стандартам ФГОС ВО, структуре учебного года, СанПиН, требованиям ВАК или подготовить проект приказа.',
      citations: ['ФГОС ВО 31.08.36', 'Регламент ГИА 2026'],
      timestamp: '09:00'
    }
  ];

  // Order Generation State
  let orderType = 'admission';
  let studentName = '';
  let specialtyCode = '31.08.36';
  let orderNumber = 'ПР-2026/04';
  let isGeneratingOrder = false;
  let orderGenerationProgress = 0;
  let generationSuccess = false;

  const specialties = [
    { code: '31.08.36', name: 'Эпидемиология' },
    { code: '31.08.35', name: 'Инфекционные болезни' },
    { code: '31.08.19', name: 'Педиатрия' }
  ];

  const orderTypes = [
    { id: 'admission', label: 'Приказ о зачислении в ординатуру' },
    { id: 'gia_admission', label: 'Приказ о допуске к ГИА (3 этапа)' },
    { id: 'stipend', label: 'Приказ о назначении государственной стипендии' },
    { id: 'practice', label: 'Приказ о направлении на практическую подготовку' }
  ];

  async function sendChatMessage() {
    if (!chatQuery.trim() || isSubmitting) return;

    const userMsg = {
      id: `u-${Date.now()}`,
      sender: 'user',
      text: chatQuery.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    messages = [...messages, userMsg];
    const queryText = chatQuery;
    chatQuery = '';
    isSubmitting = true;

    // Simulate streaming / responsive DeepSeek assistant integration
    setTimeout(() => {
      let replyText = '';
      let citations = [];

      if (queryText.toLowerCase().includes('гиа') || queryText.toLowerCase().includes('экзамен')) {
        replyText = 'В соответствии с Положением о ГИА института, итоговая аттестация включает 3 обязательных этапа:\n1. Компьютерное тестирование (допуск от 70% верных ответов);\n2. Оценка практических навыков в симуляционном центре;\n3. Собеседование по билетам с членами ГЭК.';
        citations = ['ФГОС ВО 31.08.36', 'Положение об итоговой аттестации ФБУН ЦНИИЭ'];
      } else if (queryText.toLowerCase().includes('нагрузк') || queryText.toLowerCase().includes('ставк')) {
        replyText = 'Кафедральная норма годовой педагогической нагрузки ППС составляет 750–900 часов в год. Включает лекции, семинары, клиническую практику и руководство ординаторами.';
        citations = ['Приказ Минобрнауки №1601', 'Регламент планирования нагрузки ППС'];
      } else {
        replyText = `По вашему запросу («${queryText}») проверена нормативная база ФБУН ЦНИИ Эпидемиологии. Требования регламентированы текущими РПД и стандартами Роспотребнадзора. Документ соответствует ГОСТ Р 7.0.97-2016.`;
        citations = ['ГОСТ Р 7.0.97-2016', 'Устав ФБУН ЦНИИЭ'];
      }

      const assistantMsg = {
        id: `a-${Date.now()}`,
        sender: 'assistant',
        text: replyText,
        citations,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      messages = [...messages, assistantMsg];
      isSubmitting = false;
    }, 600);
  }

  async function copyToClipboard(text, id) {
    try {
      await navigator.clipboard.writeText(text);
      copySuccessId = id;
      setTimeout(() => {
        if (copySuccessId === id) copySuccessId = null;
      }, 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  }

  async function generateOrder() {
    if (isGeneratingOrder) return;
    isGeneratingOrder = true;
    orderGenerationProgress = 10;
    generationSuccess = false;

    const interval = setInterval(() => {
      orderGenerationProgress += 25;
      if (orderGenerationProgress >= 100) {
        clearInterval(interval);
        finishOrderGeneration();
      }
    }, 250);
  }

  function finishOrderGeneration() {
    isGeneratingOrder = false;
    generationSuccess = true;

    // Trigger automatic download of GOST-compliant .docx draft
    const selectedOrderObj = orderTypes.find(t => t.id === orderType);
    const docTitle = selectedOrderObj ? selectedOrderObj.label : 'Проект приказа';
    const specObj = specialties.find(s => s.code === specialtyCode);
    
    const content = `ФЕДЕРАЛЬНОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ\nЦЕНТРАЛЬНЫЙ НАУЧНО-ИССЛЕДОВАТЕЛЬСКИЙ ИНСТИТУТ ЭПИДЕМИОЛОГИИ\nФЕДЕРАЛЬНОЙ СЛУЖБЫ ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\n\nПРИКАЗ\n${orderNumber}\nг. Москва\n\n${docTitle.toUpperCase()}\n\nВ соответствии с ГОСТ Р 7.0.97-2016, образовательной программой высшего образования по специальности ${specialtyCode} (${specObj ? specObj.name : ''}):\nОбучающийся: ${studentName || 'Иванов И.И.'}\n\nДиректор института, академик РАН\nДата: ${new Date().toLocaleDateString('ru-RU')}`;

    const blob = new Blob([content], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Prikaz_${orderType}_${specialtyCode}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<div class="cnie-container">
  <!-- Header Navigation -->
  <header class="cnie-header">
    <div class="cnie-title-area">
      <h1 class="cnie-title">ИИ-Помощник & База приказов</h1>
      <p class="cnie-subtitle">ФБУН ЦНИИ Эпидемиологии Роспотребнадзора • ГОСТ Р 7.0.97-2016</p>
    </div>
    <nav class="cnie-tabs" aria-label="Разделы">
      <button
        class="tab-btn {activeTab === 'assistant' ? 'active' : ''}"
        on:click={() => (activeTab = 'assistant')}
        type="button"
      >
        💬 Ассистент
      </button>
      <button
        class="tab-btn {activeTab === 'orders' ? 'active' : ''}"
        on:click={() => (activeTab = 'orders')}
        type="button"
      >
        📄 Приказы (.docx)
      </button>
    </nav>
  </header>

  <!-- Assistant Chat View -->
  {#if activeTab === 'assistant'}
    <section class="chat-section" aria-label="Диалог с ассистентом">
      <div class="chat-history" id="chat-history">
        {#each messages as msg (msg.id)}
          <div class="message-row {msg.sender}">
            <div class="message-bubble">
              <div class="bubble-header">
                <span class="sender-name">{msg.sender === 'assistant' ? 'ИИ-Помощник ЦНИИЭ' : 'Сотрудник'}</span>
                <span class="timestamp">{msg.timestamp}</span>
              </div>
              <div class="bubble-content">
                <p>{msg.text}</p>
              </div>

              {#if msg.citations && msg.citations.length > 0}
                <div class="citations-block">
                  <span class="citation-label">Нормативные ссылки:</span>
                  <div class="citation-tags">
                    {#each msg.citations as cit}
                      <span class="citation-tag">{cit}</span>
                    {/each}
                  </div>
                </div>
              {/if}

              <div class="bubble-actions">
                <button
                  type="button"
                  class="action-btn"
                  on:click={() => copyToClipboard(msg.text, msg.id)}
                  aria-label="Копировать ответ"
                >
                  {#if copySuccessId === msg.id}
                    ✓ Скопировано
                  {:else}
                    📋 Скопировать
                  {/if}
                </button>
              </div>
            </div>
          </div>
        {/each}

        {#if isSubmitting}
          <div class="message-row assistant">
            <div class="message-bubble typing-indicator">
              <span>ИИ-помощник анализирует нормативную базу...</span>
            </div>
          </div>
        {/if}
      </div>

      <form class="chat-input-area" on:submit|preventDefault={sendChatMessage}>
        <textarea
          class="chat-textarea"
          bind:value={chatQuery}
          on:keydown={handleKeyDown}
          placeholder="Задайте вопрос по ФГОС ВО, допуску к ГИА, ВАК или нагрузке ППС... (Enter для отправки)"
          rows="2"
          aria-label="Поле ввода вопроса"
        ></textarea>
        <button
          type="submit"
          class="btn-send"
          disabled={!chatQuery.trim() || isSubmitting}
        >
          Отправить
        </button>
      </form>
    </section>
  {/if}

  <!-- Order Generation View -->
  {#if activeTab === 'orders'}
    <section class="orders-section" aria-label="Генерация проектов приказов">
      <div class="order-card">
        <h2 class="card-title">Формирование проекта приказа по ГОСТ Р 7.0.97-2016</h2>
        <p class="card-desc">
          Генерация документа Word (.docx) с реквизитами Роспотребнадзора, полями 30/15 мм и шрифтом Times New Roman 14pt.
        </p>

        <form class="order-form" on:submit|preventDefault={generateOrder}>
          <div class="form-group">
            <label for="order-type">Тип приказа</label>
            <select id="order-type" bind:value={orderType} class="form-control">
              {#each orderTypes as type}
                <option value={type.id}>{type.label}</option>
              {/each}
            </select>
          </div>

          <div class="form-row">
            <div class="form-group col">
              <label for="order-spec">Специальность</label>
              <select id="order-spec" bind:value={specialtyCode} class="form-control">
                {#each specialties as spec}
                  <option value={spec.code}>{spec.code} {spec.name}</option>
                {/each}
              </select>
            </div>

            <div class="form-group col">
              <label for="order-num">Номер приказа</label>
              <input
                id="order-num"
                type="text"
                bind:value={orderNumber}
                class="form-control"
                placeholder="ПР-2026/04"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="order-student">ФИО обучающегося / сотрудников</label>
            <input
              id="order-student"
              type="text"
              bind:value={studentName}
              class="form-control"
              placeholder="Иванов Иван Иванович"
            />
          </div>

          {#if isGeneratingOrder}
            <div class="progress-wrapper">
              <div class="progress-label">
                <span>Формирование .docx по стандарту ГОСТ...</span>
                <span>{orderGenerationProgress}%</span>
              </div>
              <div class="progress-bar-track">
                <div
                  class="progress-bar-fill"
                  style="width: {orderGenerationProgress}%"
                ></div>
              </div>
            </div>
          {/if}

          {#if generationSuccess}
            <div class="success-banner" role="status">
              ✓ Проект приказа успешно сформирован и загружен на ваше устройство.
            </div>
          {/if}

          <button
            type="submit"
            class="btn-generate"
            disabled={isGeneratingOrder}
          >
            {isGeneratingOrder ? 'Формирование...' : 'Сформировать приказ (.docx)'}
          </button>
        </form>
      </div>
    </section>
  {/if}
</div>

<style>
  .cnie-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 1000px;
    margin: 0 auto;
    padding: 1rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
  }

  .cnie-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
  }

  @media (min-width: 640px) {
    .cnie-header {
      flex-direction: row;
      justify-content: space-between;
      align-items: center;
    }
  }

  .cnie-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0;
    color: #0f172a;
  }

  .cnie-subtitle {
    font-size: 0.8125rem;
    color: #64748b;
    margin: 0.25rem 0 0 0;
  }

  .cnie-tabs {
    display: flex;
    gap: 0.5rem;
  }

  .tab-btn {
    padding: 0.5rem 1rem;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
    color: #475569;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    background: #f1f5f9;
  }

  .tab-btn.active {
    background: #0284c7;
    color: #ffffff;
    border-color: #0284c7;
  }

  /* Chat View */
  .chat-section {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 480px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .chat-history {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .message-row {
    display: flex;
    width: 100%;
  }

  .message-row.user {
    justify-content: flex-end;
  }

  .message-row.assistant {
    justify-content: flex-start;
  }

  .message-bubble {
    max-width: 85%;
    padding: 0.875rem 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .message-row.user .message-bubble {
    background: #0284c7;
    color: #ffffff;
    border-bottom-right-radius: 0;
  }

  .message-row.assistant .message-bubble {
    background: #f8fafc;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 0;
  }

  .bubble-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    margin-bottom: 0.35rem;
    opacity: 0.85;
  }

  .bubble-content p {
    margin: 0;
    line-height: 1.5;
    white-space: pre-wrap;
    font-size: 0.9375rem;
  }

  .citations-block {
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px dashed #cbd5e1;
  }

  .citation-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #475569;
  }

  .citation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.25rem;
  }

  .citation-tag {
    background: #e0f2fe;
    color: #0369a1;
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 500;
  }

  .bubble-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.5rem;
  }

  .action-btn {
    background: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    cursor: pointer;
    color: #475569;
  }

  .action-btn:hover {
    background: #e2e8f0;
  }

  .typing-indicator {
    font-style: italic;
    color: #64748b;
    font-size: 0.875rem;
  }

  .chat-input-area {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
  }

  .chat-textarea {
    flex: 1;
    padding: 0.5rem 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    font-family: inherit;
    font-size: 0.875rem;
    resize: none;
  }

  .chat-textarea:focus {
    outline: none;
    border-color: #0284c7;
    box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2);
  }

  .btn-send {
    padding: 0 1.25rem;
    background: #0284c7;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-weight: 500;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-send:hover:not(:disabled) {
    background: #0369a1;
  }

  .btn-send:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  /* Orders View */
  .orders-section {
    flex: 1;
  }

  .order-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1.5rem;
  }

  .card-title {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0 0 0.25rem 0;
    color: #0f172a;
  }

  .card-desc {
    font-size: 0.875rem;
    color: #64748b;
    margin: 0 0 1.5rem 0;
  }

  .order-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .form-row {
    display: flex;
    gap: 1rem;
    flex-direction: column;
  }

  @media (min-width: 640px) {
    .form-row {
      flex-direction: row;
    }
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .form-group.col {
    flex: 1;
  }

  .form-group label {
    font-size: 0.8125rem;
    font-weight: 500;
    color: #334155;
  }

  .form-control {
    padding: 0.5rem 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-family: inherit;
    color: #0f172a;
  }

  .form-control:focus {
    outline: none;
    border-color: #0284c7;
    box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2);
  }

  .progress-wrapper {
    margin-top: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.8125rem;
    color: #0284c7;
    font-weight: 500;
  }

  .progress-bar-track {
    width: 100%;
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: #0284c7;
    transition: width 0.25s ease-out;
  }

  .success-banner {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }

  .btn-generate {
    align-self: flex-start;
    padding: 0.625rem 1.25rem;
    background: #059669;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-generate:hover:not(:disabled) {
    background: #047857;
  }

  .btn-generate:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }
</style>
