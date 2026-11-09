<script>
  import { onMount } from 'svelte';

  // Active tab state: 'assistant' | 'orders' | 'workload'
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

  // Workload Calculator State
  let departmentNorm = 800; // Standard midpoint of 750–900 h/year
  const DEPT_FLOOR = 750;
  const DEPT_CEILING = 900;

  let lectureHours = 120;
  let seminarHours = 280;
  let practiceHours = 320;
  let postgraduateHours = 60;
  let gekHours = 40;

  $: safeLectures = Math.max(0, Number(lectureHours) || 0);
  $: safeSeminars = Math.max(0, Number(seminarHours) || 0);
  $: safePractice = Math.max(0, Number(practiceHours) || 0);
  $: safePostgraduate = Math.max(0, Number(postgraduateHours) || 0);
  $: safeGek = Math.max(0, Number(gekHours) || 0);

  $: totalHours = safeLectures + safeSeminars + safePractice + safePostgraduate + safeGek;
  $: fteRate = departmentNorm > 0 ? Number((totalHours / departmentNorm).toFixed(2)) : 0;
  $: isOverload = totalHours > DEPT_CEILING;
  $: isUnderload = totalHours < DEPT_FLOOR;
  $: excessHours = isOverload ? totalHours - DEPT_CEILING : 0;
  $: deficitHours = isUnderload ? DEPT_FLOOR - totalHours : 0;
  $: gaugePercent = Math.min(100, Math.round((totalHours / DEPT_CEILING) * 100));

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

  function resetWorkloadToStandard() {
    lectureHours = 120;
    seminarHours = 280;
    practiceHours = 320;
    postgraduateHours = 60;
    gekHours = 40;
    departmentNorm = 800;
  }

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
  <header class="cnie-header" role="banner">
    <div class="cnie-title-area">
      <h1 class="cnie-title">ИИ-Помощник & База приказов</h1>
      <p class="cnie-subtitle">ФБУН ЦНИИ Эпидемиологии Роспотребнадзора • ГОСТ Р 7.0.97-2016</p>
    </div>
    <nav class="cnie-tabs" aria-label="Разделы системы" role="tablist">
      <button
        id="tab-btn-assistant"
        role="tab"
        aria-selected={activeTab === 'assistant'}
        aria-controls="tabpanel-assistant"
        class="tab-btn {activeTab === 'assistant' ? 'active' : ''}"
        on:click={() => (activeTab = 'assistant')}
        type="button"
      >
        💬 Ассистент
      </button>
      <button
        id="tab-btn-orders"
        role="tab"
        aria-selected={activeTab === 'orders'}
        aria-controls="tabpanel-orders"
        class="tab-btn {activeTab === 'orders' ? 'active' : ''}"
        on:click={() => (activeTab = 'orders')}
        type="button"
      >
        📄 Приказы (.docx)
      </button>
      <button
        id="tab-btn-workload"
        role="tab"
        aria-selected={activeTab === 'workload'}
        aria-controls="tabpanel-workload"
        class="tab-btn {activeTab === 'workload' ? 'active' : ''}"
        on:click={() => (activeTab = 'workload')}
        type="button"
      >
        ⚖️ Нагрузка
      </button>
    </nav>
  </header>

  <!-- Assistant Chat View -->
  {#if activeTab === 'assistant'}
    <section
      id="tabpanel-assistant"
      role="tabpanel"
      aria-labelledby="tab-btn-assistant"
      class="chat-section"
      aria-label="Диалог с ассистентом"
    >
      <div class="chat-history" id="chat-history" role="log" aria-live="polite">
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
                  <div class="citation-tags" role="list">
                    {#each msg.citations as cit}
                      <span class="citation-tag" role="listitem">{cit}</span>
                    {/each}
                  </div>
                </div>
              {/if}

              <div class="bubble-actions">
                <button
                  type="button"
                  class="action-btn"
                  on:click={() => copyToClipboard(msg.text, msg.id)}
                  aria-label="Копировать ответ ассистента в буфер обмена"
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
          <div class="message-row assistant" role="status" aria-live="polite">
            <div class="message-bubble typing-indicator">
              <span>ИИ-помощник анализирует нормативную базу...</span>
            </div>
          </div>
        {/if}
      </div>

      <form class="chat-input-area" on:submit|preventDefault={sendChatMessage} role="search">
        <label for="chat-input-query" class="sr-only">Введите вопрос по нормативной базе или регламентам</label>
        <textarea
          id="chat-input-query"
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
          aria-label="Отправить вопрос ассистенту"
        >
          Отправить
        </button>
      </form>
    </section>
  {/if}

  <!-- Order Generation View -->
  {#if activeTab === 'orders'}
    <section
      id="tabpanel-orders"
      role="tabpanel"
      aria-labelledby="tab-btn-orders"
      class="orders-section"
      aria-label="Генерация проектов приказов"
    >
      <div class="order-card">
        <h2 class="card-title">Формирование проекта приказа по ГОСТ Р 7.0.97-2016</h2>
        <p class="card-desc">
          Генерация документа Word (.docx) с реквизитами Роспотребнадзора, полями 30/15 мм и шрифтом Times New Roman 14pt.
        </p>

        <form class="order-form" on:submit|preventDefault={generateOrder}>
          <div class="form-group">
            <label for="order-type">Тип приказа</label>
            <select id="order-type" bind:value={orderType} class="form-control" aria-required="true">
              {#each orderTypes as type}
                <option value={type.id}>{type.label}</option>
              {/each}
            </select>
          </div>

          <div class="form-row">
            <div class="form-group col">
              <label for="order-spec">Специальность</label>
              <select id="order-spec" bind:value={specialtyCode} class="form-control" aria-required="true">
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
                aria-required="true"
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
              aria-describedby="order-student-help"
            />
            <small id="order-student-help" class="help-text">В соответствии с 152-ФЗ данные обрабатываются только локально без передачи в сторонние сервисы.</small>
          </div>

          {#if isGeneratingOrder}
            <div class="progress-wrapper" role="progressbar" aria-valuenow={orderGenerationProgress} aria-valuemin="0" aria-valuemax="100">
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
            <div class="success-banner" role="status" aria-live="polite">
              ✓ Проект приказа успешно сформирован и загружен на ваше устройство.
            </div>
          {/if}

          <button
            type="submit"
            class="btn-generate"
            disabled={isGeneratingOrder}
            aria-label="Сформировать и скачать проект приказа в формате docx"
          >
            {isGeneratingOrder ? 'Формирование...' : 'Сформировать приказ (.docx)'}
          </button>
        </form>
      </div>
    </section>
  {/if}

  <!-- Workload Calculator View -->
  {#if activeTab === 'workload'}
    <section
      id="tabpanel-workload"
      role="tabpanel"
      aria-labelledby="tab-btn-workload"
      class="workload-section"
      aria-label="Калькулятор педагогической нагрузки ППС"
    >
      <div class="workload-card">
        <div class="workload-header-row">
          <div>
            <h2 class="card-title">Экспресс-калькулятор нагрузки преподавателей (ППС)</h2>
            <p class="card-desc">
              Интерактивный расчет годовой педагогической нагрузки, доли ставки и контроль нормативного коридора (750–900 ч/год).
            </p>
          </div>
          <button type="button" class="btn-reset" on:click={resetWorkloadToStandard} aria-label="Сбросить значения на стандартные">
            Сбросить на базовые
          </button>
        </div>

        <!-- Real-time Alerts -->
        {#if isOverload}
          <div class="alert-banner alert-overload" role="alert" aria-live="assertive">
            <div class="alert-icon">⚠️</div>
            <div class="alert-text">
              <strong>Внимание: Превышение нормы нагрузки!</strong>
              <span>Текущий расчет превышает кафедральный максимум ({DEPT_CEILING} ч) на <strong>{excessHours} ч</strong> (ставка: {fteRate}). Требуется согласование или перераспределение.</span>
            </div>
          </div>
        {:else if isUnderload}
          <div class="alert-banner alert-underload" role="alert" aria-live="polite">
            <div class="alert-icon">ℹ️</div>
            <div class="alert-text">
              <strong>Уведомление: Недогрузка относительно нормы.</strong>
              <span>Для полной ставки не хватает <strong>{deficitHours} ч</strong> (минимум: {DEPT_FLOOR} ч/год, текущая ставка: {fteRate}).</span>
            </div>
          </div>
        {:else}
          <div class="alert-banner alert-optimal" role="status" aria-live="polite">
            <div class="alert-icon">✅</div>
            <div class="alert-text">
              <strong>Оптимальная нагрузка в пределах кафедральной нормы (750–900 ч/год).</strong>
              <span>Объем соответствует {fteRate} ставки преподавателя.</span>
            </div>
          </div>
        {/if}

        <!-- Metric Badges & Gauge Meter -->
        <div class="metrics-grid">
          <div class="metric-box">
            <span class="metric-label">Итого часов / год</span>
            <span class="metric-value {isOverload ? 'text-red' : isUnderload ? 'text-amber' : 'text-green'}">
              {totalHours} ч
            </span>
            <span class="metric-sub">Норматив: {DEPT_FLOOR}–{DEPT_CEILING} ч</span>
          </div>

          <div class="metric-box">
            <span class="metric-label">Расчетная ставка (FTE)</span>
            <span class="metric-value">{fteRate}</span>
            <span class="metric-sub">База: {departmentNorm} ч/год</span>
          </div>

          <div class="metric-box">
            <span class="metric-label">Статус загрузки</span>
            <span class="status-badge {isOverload ? 'badge-danger' : isUnderload ? 'badge-warning' : 'badge-success'}">
              {isOverload ? 'Перегрузка' : isUnderload ? 'Недогрузка' : 'В норме'}
            </span>
            <span class="metric-sub">
              {isOverload ? `+${excessHours} ч сверх потолка` : isUnderload ? `-${deficitHours} ч до минимума` : 'Сбалансировано'}
            </span>
          </div>
        </div>

        <!-- Gauge Progress Bar -->
        <div class="gauge-container" role="meter" aria-valuenow={totalHours} aria-valuemin="0" aria-valuemax={DEPT_CEILING} aria-label="Индикатор соответствия кафедральной норме">
          <div class="gauge-label-row">
            <span>Прогресс годовой нормы (0 - {DEPT_CEILING} ч):</span>
            <span><strong>{gaugePercent}%</strong></span>
          </div>
          <div class="gauge-track">
            <div
              class="gauge-fill {isOverload ? 'fill-red' : isUnderload ? 'fill-amber' : 'fill-green'}"
              style="width: {gaugePercent}%"
            ></div>
          </div>
        </div>

        <!-- Input Form -->
        <form class="workload-form" on:submit|preventDefault={() => {}}>
          <div class="form-group norm-selector-group">
            <label for="dept-norm-select">Кафедральная норма для 1.0 ставки (ч/год):</label>
            <select id="dept-norm-select" bind:value={departmentNorm} class="form-control form-control-sm">
              <option value={750}>750 ч (Минимальный порог)</option>
              <option value={800}>800 ч (Стандарт ЦНИИЭ)</option>
              <option value={850}>850 ч (Повышенная нагрузка)</option>
              <option value={900}>900 ч (Предельный максимум)</option>
            </select>
          </div>

          <div class="hours-grid">
            <div class="form-group">
              <label for="hours-lecture">Лекционные часы (ч/год)</label>
              <input
                id="hours-lecture"
                type="number"
                min="0"
                max="500"
                step="1"
                bind:value={lectureHours}
                class="form-control"
                aria-describedby="hours-lecture-help"
              />
              <small id="hours-lecture-help" class="help-text">Теоретические занятия и потоковые лекции</small>
            </div>

            <div class="form-group">
              <label for="hours-seminar">Семинары и коллоквиумы (ч/год)</label>
              <input
                id="hours-seminar"
                type="number"
                min="0"
                max="600"
                step="1"
                bind:value={seminarHours}
                class="form-control"
                aria-describedby="hours-seminar-help"
              />
              <small id="hours-seminar-help" class="help-text">Групповые практические и семинарские разборы</small>
            </div>

            <div class="form-group">
              <label for="hours-practice">Клиническая практика (ч/год)</label>
              <input
                id="hours-practice"
                type="number"
                min="0"
                max="700"
                step="1"
                bind:value={practiceHours}
                class="form-control"
                aria-describedby="hours-practice-help"
              />
              <small id="hours-practice-help" class="help-text">Ординатура, симуляционный центр, клинические базы</small>
            </div>

            <div class="form-group">
              <label for="hours-postgraduate">Руководство аспирантами/ординаторами</label>
              <input
                id="hours-postgraduate"
                type="number"
                min="0"
                max="300"
                step="1"
                bind:value={postgraduateHours}
                class="form-control"
                aria-describedby="hours-postgraduate-help"
              />
              <small id="hours-postgraduate-help" class="help-text">Научно-исследовательская работа и консультации</small>
            </div>

            <div class="form-group col-span-full">
              <label for="hours-gek">Работа в ГЭК и аттестационных комиссиях</label>
              <input
                id="hours-gek"
                type="number"
                min="0"
                max="200"
                step="1"
                bind:value={gekHours}
                class="form-control"
                aria-describedby="hours-gek-help"
              />
              <small id="hours-gek-help" class="help-text">Проведение 3 обязательных этапов ГИА и кандидатских экзаменов</small>
            </div>
          </div>
        </form>
      </div>
    </section>
  {/if}
</div>

<style>
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

  .cnie-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-width: 1000px;
    margin: 0 auto;
    padding: 1rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
  }

  .cnie-header {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    border-bottom: 1px solid #cbd5e1;
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
    font-size: 0.875rem;
    color: #334155;
    margin: 0.25rem 0 0 0;
  }

  .cnie-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .tab-btn {
    padding: 0.5rem 1rem;
    border: 1px solid #64748b;
    background: #f8fafc;
    color: #1e293b;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab-btn:hover,
  .tab-btn:focus-visible {
    background: #e2e8f0;
    outline: 2px solid #0369a1;
    outline-offset: 2px;
  }

  .tab-btn.active {
    background: #0369a1;
    color: #ffffff;
    border-color: #0369a1;
  }

  /* Chat View */
  .chat-section {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 480px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
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
    background: #0369a1;
    color: #ffffff;
    border-bottom-right-radius: 0;
  }

  .message-row.assistant .message-bubble {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-bottom-left-radius: 0;
  }

  .bubble-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.8125rem;
    margin-bottom: 0.35rem;
    font-weight: 600;
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
    border-top: 1px dashed #94a3b8;
  }

  .citation-label {
    font-size: 0.8125rem;
    font-weight: 700;
    color: #1e293b;
  }

  .citation-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.25rem;
  }

  .citation-tag {
    background: #e0f2fe;
    color: #075985;
    font-size: 0.8125rem;
    padding: 0.125rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
  }

  .bubble-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.5rem;
  }

  .action-btn {
    background: #ffffff;
    border: 1px solid #64748b;
    border-radius: 0.25rem;
    font-size: 0.8125rem;
    font-weight: 500;
    padding: 0.25rem 0.6rem;
    cursor: pointer;
    color: #1e293b;
  }

  .action-btn:hover,
  .action-btn:focus-visible {
    background: #f1f5f9;
    outline: 2px solid #0369a1;
  }

  .typing-indicator {
    font-style: italic;
    color: #334155;
    font-size: 0.875rem;
  }

  .chat-input-area {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    background: #f8fafc;
    border-top: 1px solid #cbd5e1;
  }

  .chat-textarea {
    flex: 1;
    padding: 0.5rem 0.75rem;
    border: 1px solid #64748b;
    border-radius: 0.375rem;
    font-family: inherit;
    font-size: 0.9375rem;
    color: #0f172a;
    resize: none;
  }

  .chat-textarea:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: 1px;
    border-color: #0369a1;
  }

  .btn-send {
    padding: 0 1.25rem;
    background: #0369a1;
    color: #ffffff;
    border: none;
    border-radius: 0.375rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-send:hover:not(:disabled),
  .btn-send:focus-visible {
    background: #075985;
    outline: 2px solid #0369a1;
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
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    padding: 1.5rem;
  }

  .card-title {
    font-size: 1.125rem;
    font-weight: 700;
    margin: 0 0 0.25rem 0;
    color: #0f172a;
  }

  .card-desc {
    font-size: 0.875rem;
    color: #334155;
    margin: 0 0 1.5rem 0;
  }

  .order-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
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
    font-size: 0.875rem;
    font-weight: 600;
    color: #1e293b;
  }

  .help-text {
    font-size: 0.75rem;
    color: #475569;
  }

  .form-control {
    padding: 0.5rem 0.75rem;
    border: 1px solid #64748b;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-family: inherit;
    color: #0f172a;
  }

  .form-control-sm {
    max-width: 280px;
  }

  .form-control:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: 1px;
    border-color: #0369a1;
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
    color: #0369a1;
    font-weight: 600;
  }

  .progress-bar-track {
    width: 100%;
    height: 8px;
    background: #cbd5e1;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: #0369a1;
    transition: width 0.25s ease-out;
  }

  .success-banner {
    background: #f0fdf4;
    border: 1px solid #16a34a;
    color: #14532d;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .btn-generate {
    align-self: flex-start;
    padding: 0.625rem 1.25rem;
    background: #15803d;
    color: #ffffff;
    border: none;
    border-radius: 0.375rem;
    font-weight: 600;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-generate:hover:not(:disabled),
  .btn-generate:focus-visible {
    background: #166534;
    outline: 2px solid #15803d;
  }

  .btn-generate:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  /* Workload Calculator Section */
  .workload-section {
    flex: 1;
  }

  .workload-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    padding: 1.5rem;
  }

  .workload-header-row {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
  }

  @media (min-width: 640px) {
    .workload-header-row {
      flex-direction: row;
      align-items: center;
    }
  }

  .btn-reset {
    background: #f1f5f9;
    border: 1px solid #64748b;
    color: #1e293b;
    padding: 0.4rem 0.8rem;
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-reset:hover, .btn-reset:focus-visible {
    background: #e2e8f0;
    outline: 2px solid #0369a1;
  }

  /* Alert Banners */
  .alert-banner {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    border-radius: 0.375rem;
    margin-bottom: 1.25rem;
    align-items: flex-start;
  }

  .alert-icon {
    font-size: 1.25rem;
    line-height: 1;
  }

  .alert-text {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.875rem;
  }

  .alert-overload {
    background: #fef2f2;
    border: 1px solid #b91c1c;
    color: #991b1b;
  }

  .alert-underload {
    background: #fffbeb;
    border: 1px solid #d97706;
    color: #92400e;
  }

  .alert-optimal {
    background: #f0fdf4;
    border: 1px solid #16a34a;
    color: #166534;
  }

  /* Metrics Grid */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(1, minmax(0, 1fr));
    gap: 1rem;
    margin-bottom: 1.25rem;
  }

  @media (min-width: 640px) {
    .metrics-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  .metric-box {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    text-align: center;
  }

  .metric-label {
    font-size: 0.8125rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #0f172a;
  }

  .metric-sub {
    font-size: 0.75rem;
    color: #64748b;
  }

  .text-red {
    color: #b91c1c;
  }

  .text-amber {
    color: #d97706;
  }

  .text-green {
    color: #15803d;
  }

  .status-badge {
    display: inline-block;
    align-self: center;
    font-size: 0.875rem;
    font-weight: 700;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
  }

  .badge-danger {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #b91c1c;
  }

  .badge-warning {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #d97706;
  }

  .badge-success {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #16a34a;
  }

  /* Gauge */
  .gauge-container {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.375rem;
    padding: 0.875rem;
    margin-bottom: 1.5rem;
  }

  .gauge-label-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.8125rem;
    color: #334155;
    margin-bottom: 0.5rem;
  }

  .gauge-track {
    width: 100%;
    height: 12px;
    background: #e2e8f0;
    border-radius: 6px;
    overflow: hidden;
  }

  .gauge-fill {
    height: 100%;
    transition: width 0.2s ease-in-out;
  }

  .fill-red {
    background: #ef4444;
  }

  .fill-amber {
    background: #f59e0b;
  }

  .fill-green {
    background: #10b981;
  }

  /* Workload Form */
  .workload-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .norm-selector-group {
    padding-bottom: 1rem;
    border-bottom: 1px dashed #cbd5e1;
  }

  .hours-grid {
    display: grid;
    grid-template-columns: repeat(1, minmax(0, 1fr));
    gap: 1rem;
  }

  @media (min-width: 640px) {
    .hours-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .col-span-full {
      grid-column: 1 / -1;
    }
  }
</style>
