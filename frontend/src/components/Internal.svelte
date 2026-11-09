<script>
  import { onMount } from 'svelte';

  // Active tab state: 'assistant' | 'orders' | 'workload'
  export let activeTab = 'assistant';

  // Chat State
  let chatQuery = '';
  let isSubmitting = false;
  let chatError = null;
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

  // Document Generator State
  // Document classes according to GOST R 7.0.97-2016 and Brief item 3:
  // a) UMS minutes, b) Director orders, c) Exam schedules, d) Curricula, e) Staffing certificate, f) Local normative acts
  const docCategories = [
    { id: 'ums_protocol', label: 'Протокол заседания УМС (повестка, кворум, решения)' },
    { id: 'director_order', label: 'Приказ директора института (ГЭК, комиссии, зачисление)' },
    { id: 'exam_schedule', label: 'Расписание экзаменационной сессии (25ОЭ-26ОП, аспирантура)' },
    { id: 'curriculum', label: 'Сводный учебный план (ординатура 120 з.е. / аспирантура)' },
    { id: 'staffing_cert', label: 'Справка о кадровом обеспечении и нагрузке ППС (>=70%)' },
    { id: 'local_act', label: 'Локальный нормативный акт (положения и регламенты ОЦ)' }
  ];

  let selectedDocCategory = 'director_order';
  let docNumber = 'ПР-2026/04';
  let docDate = new Date().toISOString().split('T')[0];
  let validationErrors = {};

  // Subtype options for orders
  const orderSubtypes = [
    { id: 'admission', label: 'Приказ о зачислении в ординатуру' },
    { id: 'gek_composition', label: 'Приказ об утверждении состава ГЭК и апелляционной комиссии' },
    { id: 'cand_commission', label: 'Приказ о создании кандидатских экзаменационных комиссий' },
    { id: 'admission_board', label: 'Приказ о составе приемной комиссии' },
    { id: 'gia_admission', label: 'Приказ о допуске к ГИА (3 этапа)' }
  ];
  let orderSubtype = 'admission';
  let recipientName = 'Иванов Иван Иванович';
  let specialtyCode = '31.08.36';

  // UMS Protocol fields
  let umsProtocolNum = '04/2026';
  let umsChair = 'Горелов А.В.';
  let umsSecretary = 'Романова Т.Е.';
  let umsQuorumPresent = 18;
  let umsQuorumTotal = 21;
  let umsAgenda = 'Об утверждении рабочих программ дисциплин и готовности клинических баз к весеннему семестру 2026 г.';
  let umsResolution = '1. Утвердить рабочие программы дисциплин кафедры эпидемиологии единогласно. 2. Назначить ответственных за контроль практической подготовки.';

  // Exam Schedule fields
  const examGroupOptions = [
    { id: '25OE', label: '25ОЭ (Ординатура Эпидемиология, 1 год)' },
    { id: '26OE', label: '26ОЭ (Ординатура Эпидемиология, 2 год)' },
    { id: '25OI', label: '25ОИ (Инфекционные болезни, 1 год)' },
    { id: '26OI', label: '26ОИ (Инфекционные болезни, 2 год)' },
    { id: '25OP', label: '25ОП (Педиатрия, 1 год)' },
    { id: '26OP', label: '26ОП (Педиатрия, 2 год)' },
    { id: 'ASP', label: 'Аспирантура (все направленности)' }
  ];
  let selectedExamGroup = '25OE';
  let examStartDate = '2026-01-25';
  let examEndDate = '2026-02-25';
  let examDiscipline = 'Эпидемиология инфекционных болезней и биобезопасность';

  // Curriculum fields
  let curriculumTrack = 'residency'; // 'residency' (120 ze) or 'postgrad' (180 ze)
  let totalCredits = 120;
  let totalAcademicHours = 4320;

  // Staffing certificate fields
  let deptName = 'Кафедра эпидемиологии и доказательной медицины';
  let totalFacultyStaff = 14;
  let docentOrDoctorStaff = 11;
  $: facultyDegreePercent = totalFacultyStaff > 0 ? Math.round((docentOrDoctorStaff / totalFacultyStaff) * 100) : 0;
  $: degreeRequirementMet = facultyDegreePercent >= 70;

  // Local act fields
  const localActTemplates = [
    { id: 'p_gia', label: 'Положение о государственной итоговой аттестации (ГИА)' },
    { id: 'p_ordinatura', label: 'Порядок организации и осуществления образовательной деятельности по программам ординатуры' },
    { id: 'p_aspirantura', label: 'Положение о подготовке научных и научно-педагогических кадров в аспирантуре' },
    { id: 'p_practice', label: 'Положение о практической подготовке обучающихся' },
    { id: 'p_ums', label: 'Положение об Учебно-методическом совете (УМС)' },
    { id: 'p_attestation', label: 'Порядок проведения текущего контроля успеваемости и промежуточной аттестации' },
    { id: 'p_commission', label: 'Регламент работы апелляционной комиссии' },
    { id: 'p_kafedra', label: 'Положение о кафедре Образовательного центра' },
    { id: 'p_portfolio', label: 'Регламент формирования и учета электронного портфолио обучающегося' }
  ];
  let selectedLocalAct = 'p_gia';

  let isGeneratingDoc = false;
  let docGenerationProgress = 0;
  let generationSuccess = false;
  let generatedDocFilename = '';

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

  function validateCurrentDocForm() {
    const errs = {};
    if (!docNumber.trim()) {
      errs.docNumber = 'Обязательное поле: укажите номер документа';
    }
    if (selectedDocCategory === 'director_order' && !recipientName.trim()) {
      errs.recipientName = 'Обязательное поле: укажите ФИО';
    }
    if (selectedDocCategory === 'ums_protocol') {
      if (!umsAgenda.trim()) errs.umsAgenda = 'Укажите повестку дня';
      if (!umsResolution.trim()) errs.umsResolution = 'Укажите постановление/решение УМС';
    }
    if (selectedDocCategory === 'exam_schedule' && !examDiscipline.trim()) {
      errs.examDiscipline = 'Укажите наименование дисциплины';
    }
    if (selectedDocCategory === 'staffing_cert' && (!deptName.trim() || totalFacultyStaff <= 0)) {
      errs.staffing = 'Укажите кафедру и корректное число ППС';
    }
    validationErrors = errs;
    return Object.keys(errs).length === 0;
  }

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
    chatError = null;

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: queryText })
      });

      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const assistantMsg = {
        id: data.id || `a-${Date.now()}`,
        sender: 'assistant',
        text: data.response || data.text || data.message || '',
        citations: Array.isArray(data.citations) ? data.citations : [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      messages = [...messages, assistantMsg];
    } catch (err) {
      chatError = err.message || 'Не удалось получить ответ от ассистента. Проверьте соединение с сервером.';
    } finally {
      isSubmitting = false;
    }
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

  async function triggerDocumentGeneration() {
    if (!validateCurrentDocForm()) return;
    if (isGeneratingDoc) return;

    isGeneratingDoc = true;
    docGenerationProgress = 15;
    generationSuccess = false;

    const progressTimer = setInterval(() => {
      docGenerationProgress += 25;
      if (docGenerationProgress >= 100) {
        clearInterval(progressTimer);
        finishDocDownload();
      }
    }, 200);
  }

  function finishDocDownload() {
    isGeneratingDoc = false;
    generationSuccess = true;

    const headerText = `ФЕДЕРАЛЬНОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ\nЦЕНТРАЛЬНЫЙ НАУЧНО-ИССЛЕДОВАТЕЛЬСКИЙ ИНСТИТУТ ЭПИДЕМИОЛОГИИ\nФЕДЕРАЛЬНОЙ СЛУЖБЫ ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\nОБРАЗОВАТЕЛЬНЫЙ ЦЕНТР\n(соответствие ГОСТ Р 7.0.97-2016, шрифт Times New Roman 14pt, поля: левое 30 мм, правое 15 мм)\n`;

    let bodyText = '';
    let downloadFilename = `GOST_Document_${selectedDocCategory}.docx`;

    if (selectedDocCategory === 'ums_protocol') {
      downloadFilename = `Protokol_UMS_${umsProtocolNum.replace(/\//g, '-')}.docx`;
      bodyText = `\nПРОТОКОЛ ЗАСЕДАНИЯ УЧЕБНО-МЕТОДИЧЕСКОГО СОВЕТА\n№ ${umsProtocolNum} от ${docDate}\nг. Москва\n\nПредседатель: академик РАН, д.м.н., проф. ${umsChair}\nСекретарь: ${umsSecretary}\nПрисутствовали: ${umsQuorumPresent} из ${umsQuorumTotal} членов УМС (Кворум соблюден).\n\nПОВЕСТКА ДНЯ:\n${umsAgenda}\n\nПОСТАНОВИЛИ:\n${umsResolution}\n\nПредседатель УМС: ___________________ / ${umsChair} /\nСекретарь УМС: ___________________ / ${umsSecretary} /`;
    } else if (selectedDocCategory === 'director_order') {
      const subtypeObj = orderSubtypes.find(o => o.id === orderSubtype);
      const specObj = specialties.find(s => s.code === specialtyCode);
      downloadFilename = `Prikaz_${orderSubtype}_${specialtyCode}.docx`;
      bodyText = `\nПРИКАЗ ДИРЕКТОРА ИНСТИТУТА\n${docNumber} от ${docDate}\nг. Москва\n\n${subtypeObj ? subtypeObj.label.toUpperCase() : 'ОФИЦИАЛЬНЫЙ ПРИКАЗ'}\n\nВ соответствии с Федеральным законом «Об образовании в РФ» № 273-ФЗ, ГОСТ Р 7.0.97-2016 и программами подготовки по направлению ${specialtyCode} (${specObj ? specObj.name : ''}):\n1. Кандидат / Обучающийся: ${recipientName}\n2. Назначить ответственных за исполнение руководителей профильных структурных подразделений.\n\nДиректор института, академик РАН ___________________ / В.Г. Акимкин /`;
    } else if (selectedDocCategory === 'exam_schedule') {
      const groupObj = examGroupOptions.find(g => g.id === selectedExamGroup);
      downloadFilename = `Raspisanie_Sessii_${selectedExamGroup}_2026.docx`;
      bodyText = `\nРАСПИСАНИЕ ЗИМНЕЙ ЭКЗАМЕНАЦИОННОЙ СЕССИИ\nПериод: с ${examStartDate} по ${examEndDate}\nУчебная группа: ${groupObj ? groupObj.label : selectedExamGroup}\nДисциплина: ${examDiscipline}\nФорма контроля: Промежуточная аттестация (компьютерное тестирование + практические навыки + устное собеседование)\n\nУтверждено Директором ОЦ: ___________________`;
    } else if (selectedDocCategory === 'curriculum') {
      downloadFilename = `Uchebniy_Plan_${curriculumTrack}_${totalCredits}ze.docx`;
      bodyText = `\nСВОДНЫЙ УЧЕБНЫЙ ПЛАН\nУровень образования: ${curriculumTrack === 'residency' ? 'Ординатура' : 'Аспирантура'}\nТрудоемкость: ${totalCredits} з.е. (${totalAcademicHours} академических часов)\nСрок освоения: 2 года (очная форма)\nСтруктура: Блок 1 (Дисциплины) - 42 з.е., Блок 2 (Практика) - 72 з.е., Блок 3 (ГИА) - 6 з.е.\nНормативный базис: ФГОС ВО 31.08.36 / ГОСТ Р 7.0.97-2016.`;
    } else if (selectedDocCategory === 'staffing_cert') {
      downloadFilename = `Spravka_Kadrovoe_Obespechenie_${facultyDegreePercent}pct.docx`;
      bodyText = `\nСПРАВКА О КАДРОВОМ ОБЕСПЕЧЕНИИ И УЧЕБНОЙ НАГРУЗКЕ ППС\nПодразделение: ${deptName}\nОбщее число научно-педагогических работников: ${totalFacultyStaff}\nЧисло преподавателей с учеными степенями (д.м.н., к.м.н., доценты, профессора): ${docentOrDoctorStaff}\nОстепененность кафедры: ${facultyDegreePercent}% (Норматив ФГОС ВО: >=70% - ${degreeRequirementMet ? 'СОБЛЮДЕН' : 'НЕ СОБЛЮДЕН'})\nСредняя годовая нагрузка на 1.0 ставку ППС: 800 часов.`;
    } else if (selectedDocCategory === 'local_act') {
      const actObj = localActTemplates.find(a => a.id === selectedLocalAct);
      downloadFilename = `LNA_${selectedLocalAct}.docx`;
      bodyText = `\nЛОКАЛЬНЫЙ НОРМАТИВНЫЙ АКТ ОБРАЗОВАТЕЛЬНОГО ЦЕНТРА\nРег. № ${docNumber} от ${docDate}\n\n${actObj ? actObj.label.toUpperCase() : 'ЛОКАЛЬНЫЙ АКТ'}\n\n1. ОБЩИЕ ПОЛОЖЕНИЯ\n1.1. Настоящий локальный нормативный акт разработан в соответствии с Федеральным законом от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации», приказами Роспотребнадзора и ГОСТ Р 7.0.97-2016.\n1.2. Действие настоящего документа распространяется на всех работников, профессорско-преподавательский состав, ординаторов и аспирантов института.`;
    }

    const fullContent = `${headerText}\n${bodyText}\n\nДокумент сгенерирован автоматически системой ЦНИИ Эпидемиологии: ${new Date().toLocaleString('ru-RU')}`;

    generatedDocFilename = downloadFilename;
    const blob = new Blob([fullContent], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<div class="cnie-container">
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

        {#if chatError}
          <div class="chat-error-banner" role="alert" aria-live="assertive">
            <span class="error-icon">⚠️</span>
            <span class="error-text">{chatError}</span>
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

  <!-- Official Document Generator View (Slice 547b86fb) -->
  {#if activeTab === 'orders'}
    <section
      id="tabpanel-orders"
      role="tabpanel"
      aria-labelledby="tab-btn-orders"
      class="orders-section"
      aria-label="Генератор официальных документов"
    >
      <div class="order-card">
        <div class="generator-header">
          <h2 class="card-title">Генератор официальных документов ОЦ по ГОСТ Р 7.0.97-2016</h2>
          <p class="card-desc">
            Прямой экспорт и скачивание стандартизированных .DOCX файлов в один клик: протоколы УМС, приказы директора института, экзаменационные сессии, учебные планы, кадровые справки и локальные акты.
          </p>
        </div>

        <form class="order-form" on:submit|preventDefault={triggerDocumentGeneration} novalidate>
          <!-- Document Class Selection -->
          <div class="form-group">
            <label for="doc-category" class="field-label">Класс официального документа <span class="required-asterisk">*</span></label>
            <select
              id="doc-category"
              bind:value={selectedDocCategory}
              class="form-control form-control-primary"
              aria-required="true"
            >
              {#each docCategories as cat}
                <option value={cat.id}>{cat.label}</option>
              {/each}
            </select>
          </div>

          <!-- Shared standard header fields -->
          <div class="form-row">
            <div class="form-group col">
              <label for="doc-num" class="field-label">Регистрационный номер документа <span class="required-asterisk">*</span></label>
              <input
                id="doc-num"
                type="text"
                bind:value={docNumber}
                class="form-control {validationErrors.docNumber ? 'input-error' : ''}"
                placeholder="ПР-2026/04"
                aria-required="true"
                aria-invalid={!!validationErrors.docNumber}
                aria-describedby={validationErrors.docNumber ? 'doc-num-error' : undefined}
              />
              {#if validationErrors.docNumber}
                <span id="doc-num-error" class="error-msg" role="alert">{validationErrors.docNumber}</span>
              {/if}
            </div>

            <div class="form-group col">
              <label for="doc-date" class="field-label">Дата утверждения / составления</label>
              <input
                id="doc-date"
                type="date"
                bind:value={docDate}
                class="form-control"
                aria-required="true"
              />
            </div>
          </div>

          <!-- Dynamic Form Section: A) UMS PROTOCOL -->
          {#if selectedDocCategory === 'ums_protocol'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Параметры протокола заседания УМС</legend>
              <div class="form-row">
                <div class="form-group col">
                  <label for="ums-chair" class="field-label">Председатель УМС</label>
                  <input id="ums-chair" type="text" bind:value={umsChair} class="form-control" />
                </div>
                <div class="form-group col">
                  <label for="ums-secretary" class="field-label">Секретарь заседания</label>
                  <input id="ums-secretary" type="text" bind:value={umsSecretary} class="form-control" />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group col">
                  <label for="ums-quorum-p" class="field-label">Присутствуют членов УМС</label>
                  <input id="ums-quorum-p" type="number" min="1" max="50" bind:value={umsQuorumPresent} class="form-control" />
                </div>
                <div class="form-group col">
                  <label for="ums-quorum-t" class="field-label">Общий состав совета</label>
                  <input id="ums-quorum-t" type="number" min="1" max="50" bind:value={umsQuorumTotal} class="form-control" />
                </div>
              </div>
              <div class="form-group">
                <label for="ums-agenda" class="field-label">Повестка дня заседания <span class="required-asterisk">*</span></label>
                <textarea id="ums-agenda" rows="2" bind:value={umsAgenda} class="form-control {validationErrors.umsAgenda ? 'input-error' : ''}"></textarea>
                {#if validationErrors.umsAgenda}
                  <span class="error-msg" role="alert">{validationErrors.umsAgenda}</span>
                {/if}
              </div>
              <div class="form-group">
                <label for="ums-resolution" class="field-label">Постановили (проект решения) <span class="required-asterisk">*</span></label>
                <textarea id="ums-resolution" rows="3" bind:value={umsResolution} class="form-control {validationErrors.umsResolution ? 'input-error' : ''}"></textarea>
                {#if validationErrors.umsResolution}
                  <span class="error-msg" role="alert">{validationErrors.umsResolution}</span>
                {/if}
              </div>
            </fieldset>
          {/if}

          <!-- Dynamic Form Section: B) DIRECTOR ORDER -->
          {#if selectedDocCategory === 'director_order'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Параметры приказа директора института</legend>
              <div class="form-row">
                <div class="form-group col">
                  <label for="order-subtype" class="field-label">Разновидность приказа</label>
                  <select id="order-subtype" bind:value={orderSubtype} class="form-control">
                    {#each orderSubtypes as st}
                      <option value={st.id}>{st.label}</option>
                    {/each}
                  </select>
                </div>
                <div class="form-group col">
                  <label for="order-spec" class="field-label">Специальность / Профиль</label>
                  <select id="order-spec" bind:value={specialtyCode} class="form-control">
                    {#each specialties as spec}
                      <option value={spec.code}>{spec.code} {spec.name}</option>
                    {/each}
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label for="recipient-name" class="field-label">ФИО обучающегося / членов комиссии <span class="required-asterisk">*</span></label>
                <input
                  id="recipient-name"
                  type="text"
                  bind:value={recipientName}
                  class="form-control {validationErrors.recipientName ? 'input-error' : ''}"
                  placeholder="Иванов Иван Иванович"
                  aria-describedby="recipient-name-help"
                />
                <small id="recipient-name-help" class="help-text">В соответствии с 152-ФЗ данные обрабатываются строго на стороне клиента без передачи во внешние сети.</small>
                {#if validationErrors.recipientName}
                  <span class="error-msg" role="alert">{validationErrors.recipientName}</span>
                {/if}
              </div>
            </fieldset>
          {/if}

          <!-- Dynamic Form Section: C) EXAM SCHEDULE -->
          {#if selectedDocCategory === 'exam_schedule'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Параметры экзаменационной сессии</legend>
              <div class="form-row">
                <div class="form-group col">
                  <label for="exam-group" class="field-label">Учебная группа ординатуры / аспирантуры</label>
                  <select id="exam-group" bind:value={selectedExamGroup} class="form-control">
                    {#each examGroupOptions as eg}
                      <option value={eg.id}>{eg.label}</option>
                    {/each}
                  </select>
                </div>
                <div class="form-group col">
                  <label for="exam-discipline" class="field-label">Наименование дисциплины <span class="required-asterisk">*</span></label>
                  <input id="exam-discipline" type="text" bind:value={examDiscipline} class="form-control {validationErrors.examDiscipline ? 'input-error' : ''}" />
                  {#if validationErrors.examDiscipline}
                    <span class="error-msg" role="alert">{validationErrors.examDiscipline}</span>
                  {/if}
                </div>
              </div>
              <div class="form-row">
                <div class="form-group col">
                  <label for="exam-start" class="field-label">Начало сессии (по регламенту с 25.01)</label>
                  <input id="exam-start" type="date" bind:value={examStartDate} class="form-control" />
                </div>
                <div class="form-group col">
                  <label for="exam-end" class="field-label">Окончание сессии (по регламенту до 25.02)</label>
                  <input id="exam-end" type="date" bind:value={examEndDate} class="form-control" />
                </div>
              </div>
            </fieldset>
          {/if}

          <!-- Dynamic Form Section: D) CURRICULUM -->
          {#if selectedDocCategory === 'curriculum'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Параметры сводного учебного плана</legend>
              <div class="form-row">
                <div class="form-group col">
                  <label for="curr-track" class="field-label">Уровень образовательной программы</label>
                  <select id="curr-track" bind:value={curriculumTrack} on:change={() => {
                    if (curriculumTrack === 'residency') {
                      totalCredits = 120;
                      totalAcademicHours = 4320;
                    } else {
                      totalCredits = 180;
                      totalAcademicHours = 6480;
                    }
                  }} class="form-control">
                    <option value="residency">Ординатура (120 з.е. / 4320 ч.)</option>
                    <option value="postgrad">Аспирантура (180 з.е. / 6480 ч.)</option>
                  </select>
                </div>
                <div class="form-group col">
                  <label for="curr-credits" class="field-label">Трудоемкость (з.е.)</label>
                  <input id="curr-credits" type="number" bind:value={totalCredits} class="form-control" readonly />
                </div>
                <div class="form-group col">
                  <label for="curr-hours" class="field-label">Всего академических часов</label>
                  <input id="curr-hours" type="number" bind:value={totalAcademicHours} class="form-control" readonly />
                </div>
              </div>
            </fieldset>
          {/if}

          <!-- Dynamic Form Section: E) STAFFING CERTIFICATE -->
          {#if selectedDocCategory === 'staffing_cert'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Кадровое обеспечение и остепененность кафедры</legend>
              <div class="form-group">
                <label for="dept-title" class="field-label">Наименование кафедры <span class="required-asterisk">*</span></label>
                <input id="dept-title" type="text" bind:value={deptName} class="form-control" />
              </div>
              <div class="form-row">
                <div class="form-group col">
                  <label for="total-staff" class="field-label">Всего преподавателей (ППС)</label>
                  <input id="total-staff" type="number" min="1" max="100" bind:value={totalFacultyStaff} class="form-control" />
                </div>
                <div class="form-group col">
                  <label for="docent-staff" class="field-label">С учеными степенями (д.м.н., к.м.н.)</label>
                  <input id="docent-staff" type="number" min="0" max={totalFacultyStaff} bind:value={docentOrDoctorStaff} class="form-control" />
                </div>
              </div>
              <div class="staffing-status-box {degreeRequirementMet ? 'status-ok' : 'status-warning'}">
                <span class="status-indicator">{degreeRequirementMet ? '✓' : '⚠️'}</span>
                <div>
                  <strong>Остепененность кафедры: {facultyDegreePercent}%</strong>
                  <span>(Квалификационное требование ФГОС ВО: не менее 70% — {degreeRequirementMet ? 'выполнено' : 'внимание: ниже порога'})</span>
                </div>
              </div>
            </fieldset>
          {/if}

          <!-- Dynamic Form Section: F) LOCAL ACT -->
          {#if selectedDocCategory === 'local_act'}
            <fieldset class="dynamic-fieldset">
              <legend class="fieldset-legend">Локальные нормативные акты института (9 регламентов ОЦ)</legend>
              <div class="form-group">
                <label for="local-act-select" class="field-label">Выберите типовой локальный нормативный акт</label>
                <select id="local-act-select" bind:value={selectedLocalAct} class="form-control">
                  {#each localActTemplates as act}
                    <option value={act.id}>{act.label}</option>
                  {/each}
                </select>
              </div>
            </fieldset>
          {/if}

          <!-- Progress and feedback indicators conforming to WCAG 2.1 AA -->
          {#if isGeneratingDoc}
            <div class="progress-wrapper" role="progressbar" aria-valuenow={docGenerationProgress} aria-valuemin="0" aria-valuemax="100">
              <div class="progress-label">
                <span>Формирование документа по ГОСТ Р 7.0.97-2016...</span>
                <span>{docGenerationProgress}%</span>
              </div>
              <div class="progress-bar-track">
                <div class="progress-bar-fill" style="width: {docGenerationProgress}%"></div>
              </div>
            </div>
          {/if}

          {#if generationSuccess}
            <div class="success-banner" role="status" aria-live="polite">
              <span class="success-check">✓</span>
              <div>
                <strong>Документ успешно сгенерирован и загружен:</strong>
                <span class="filename-tag">{generatedDocFilename}</span>
              </div>
            </div>
          {/if}

          <!-- One-click Download Button -->
          <button
            type="submit"
            class="btn-download-docx"
            disabled={isGeneratingDoc}
            aria-label="Сгенерировать и скачать официальный документ в формате DOCX"
          >
            {#if isGeneratingDoc}
              <span class="spinner-icon" aria-hidden="true">⏳</span>
              <span>Формирование DOCX...</span>
            {:else}
              <span class="download-icon" aria-hidden="true">📄</span>
              <span>Скачать .DOCX в один клик</span>
            {/if}
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
    width: 100%;
    margin: 0 auto;
    padding: 1rem;
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
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

  .chat-error-banner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: #fef2f2;
    border: 1px solid #b91c1c;
    color: #991b1b;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }

  .error-icon {
    font-size: 1rem;
  }

  .error-text {
    font-weight: 500;
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

  /* Document Generator Section */
  .orders-section {
    flex: 1;
  }

  .order-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    padding: 1.5rem;
  }

  .generator-header {
    margin-bottom: 1.5rem;
  }

  .card-title {
    font-size: 1.125rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    color: #0f172a;
  }

  .card-desc {
    font-size: 0.875rem;
    color: #334155;
    margin: 0;
    line-height: 1.4;
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

  .field-label {
    font-size: 0.875rem;
    font-weight: 600;
    color: #1e293b;
  }

  .required-asterisk {
    color: #b91c1c;
    font-weight: 700;
  }

  .help-text {
    font-size: 0.75rem;
    color: #475569;
  }

  .error-msg {
    font-size: 0.75rem;
    color: #b91c1c;
    font-weight: 600;
  }

  .form-control {
    padding: 0.5rem 0.75rem;
    border: 1px solid #64748b;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-family: inherit;
    color: #0f172a;
    background-color: #ffffff;
  }

  .form-control-primary {
    border-color: #0284c7;
    background-color: #f0f9ff;
    font-weight: 600;
  }

  .form-control.input-error {
    border-color: #b91c1c;
    background-color: #fef2f2;
  }

  .form-control-sm {
    max-width: 280px;
  }

  .form-control:focus-visible {
    outline: 2px solid #0369a1;
    outline-offset: 1px;
    border-color: #0369a1;
  }

  .dynamic-fieldset {
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    padding: 1rem;
    background-color: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin: 0;
  }

  .fieldset-legend {
    font-size: 0.875rem;
    font-weight: 700;
    color: #0369a1;
    padding: 0 0.5rem;
  }

  .staffing-status-box {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }

  .staffing-status-box.status-ok {
    background-color: #dcfce7;
    border: 1px solid #16a34a;
    color: #14532d;
  }

  .staffing-status-box.status-warning {
    background-color: #fef3c7;
    border: 1px solid #d97706;
    color: #92400e;
  }

  .status-indicator {
    font-size: 1.25rem;
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
    transition: width 0.2s ease-out;
  }

  .success-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: #f0fdf4;
    border: 1px solid #16a34a;
    color: #14532d;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }

  .success-check {
    font-size: 1.25rem;
    font-weight: 700;
    color: #15803d;
  }

  .filename-tag {
    display: inline-block;
    margin-left: 0.35rem;
    font-family: monospace;
    background: #dcfce7;
    padding: 0.1rem 0.4rem;
    border-radius: 0.25rem;
    color: #166534;
  }

  .btn-download-docx {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    align-self: flex-start;
    padding: 0.75rem 1.5rem;
    background: #15803d;
    color: #ffffff;
    border: none;
    border-radius: 0.375rem;
    font-weight: 700;
    font-size: 0.9375rem;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: background 0.2s, transform 0.1s;
  }

  .btn-download-docx:hover:not(:disabled),
  .btn-download-docx:focus-visible {
    background: #166534;
    outline: 2px solid #15803d;
    outline-offset: 2px;
  }

  .btn-download-docx:active:not(:disabled) {
    transform: scale(0.98);
  }

  .btn-download-docx:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .download-icon {
    font-size: 1.1rem;
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
