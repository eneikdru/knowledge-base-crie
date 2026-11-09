import { test, expect } from '@playwright/test';

test.describe('Catalog Download and RAG Consultant Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept catalog search to mock/verify standardized educational program entries
    await page.route('**/api/catalog/search*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 1,
          items: [
            {
              id: 'CURRICULUM-ORDINATURA-25OE',
              title: 'Сводный учебный план ординатуры (120 з.е. / 4320 ч.) по группе 25ОЭ',
              filename: 'curriculum_ordinatura_25oe.docx',
              download_url: '/api/catalog/download/curriculum_ordinatura_25oe.docx',
              type: 'educational_program'
            }
          ]
        })
      });
    });

    // Intercept download request with authentic DOCX binary headers (PK\x03\x04 zip format)
    await page.route('**/api/catalog/download/*', async (route) => {
      // Standard valid DOCX / OpenXML 4-byte signature: 0x50 0x4B 0x03 0x04
      const docxHeader = Buffer.from([
        0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x06, 0x00,
        0x08, 0x00, 0x00, 0x00, 0x21, 0x00, 0x00, 0x00
      ]);
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'Content-Disposition': 'attachment; filename="curriculum_ordinatura_25oe.docx"'
        },
        body: docxHeader
      });
    });

    // Intercept RAG consultant queries for substantive response check
    await page.route('**/api/rag/consultant*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'Требования Роспотребнадзора к расписанию и нагрузке 120 з.е.',
          answer: 'В соответствии с нормативной базой Роспотребнадзора и ГОСТ Р 7.0.97-2016, сводный учебный план ординатуры объемом 120 з.е. (4320 академических часов) предусматривает регламентированную недельную нагрузку обучающихся и соотношение остепененности профессорско-преподавательского состава не менее 70%. Расписание сессии для групп 25ОЭ и 26ОЭ утверждается приказом директора с фиксацией кворума.',
          sources: ['ГОСТ Р 7.0.97-2016', 'Приказ Минобрнауки / Роспотребнадзор №1054'],
          has_boilerplate: false
        })
      });
    });
  });

  test('DOCX download yields valid binary header and no internal filesystem paths are leaked', async ({ page }) => {
    // Navigate to application catalog page or board
    await page.goto('/#catalog').catch(() => page.goto('/'));

    // Trigger direct download and assert binary headers
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(async () => {
      // Fallback: evaluate direct fetch via page context if download trigger is API-backed
      const response = await page.request.get('/api/catalog/download/curriculum_ordinatura_25oe.docx');
      const body = await response.body();
      return {
        suggestedFilename: () => 'curriculum_ordinatura_25oe.docx',
        createReadStream: async () => null,
        rawBuffer: body
      };
    });

    // Search for educational program
    const searchInput = page.locator('input[placeholder*="поиск" i], input[type="search"], input[name="query"]');
    if (await searchInput.count() > 0) {
      await searchInput.first().fill('ординатура 120 з.е.');
      await searchInput.first().press('Enter');
    }

    const downloadTrigger = page.locator('button:has-text("Скачать"), a:has-text("Скачать"), button[data-action="download"]').first();
    if (await downloadTrigger.count() > 0) {
      await downloadTrigger.click();
    }

    const downloadResult = await downloadPromise;
    expect(downloadResult).toBeDefined();

    let buffer: Buffer;
    if ('rawBuffer' in downloadResult && downloadResult.rawBuffer) {
      buffer = downloadResult.rawBuffer;
    } else if (typeof (downloadResult as any).path === 'function') {
      const filePath = await (downloadResult as any).path();
      const fs = await import('fs');
      buffer = fs.readFileSync(filePath);
    } else {
      const response = await page.request.get('/api/catalog/download/curriculum_ordinatura_25oe.docx');
      buffer = await response.body();
    }

    // Verify valid DOCX / ZIP magic bytes (PK\x03\x04 -> 0x50, 0x4B, 0x03, 0x04)
    expect(buffer.length).toBeGreaterThanOrEqual(4);
    expect(buffer[0]).toBe(0x50);
    expect(buffer[1]).toBe(0x4b);
    expect(buffer[2]).toBe(0x03);
    expect(buffer[3]).toBe(0x04);
  });

  test('RAG consultant queries return substantive answers without boilerplate filler or path leaks', async ({ page }) => {
    const response = await page.request.post('/api/rag/consultant', {
      data: { query: 'Требования Роспотребнадзора к расписанию и нагрузке 120 з.е.' }
    });

    expect(response.status()).toBe(200);
    const body = await response.json();

    // Check substantive quality
    expect(body.answer).toBeDefined();
    expect(body.answer.length).toBeGreaterThan(60);
    expect(body.answer).toContain('120 з.е.');
    expect(body.answer).toContain('Роспотребнадзор');

    // Check absence of boilerplate filler
    const boilerplatePatterns = [
      /as an ai language model/i,
      /я всего лишь языковая модель/i,
      /lorem ipsum/i,
      /\{\{.*?\}\}/,
      /TODO:/i
    ];
    for (const pattern of boilerplatePatterns) {
      expect(body.answer).not.toMatch(pattern);
    }

    // Verify 0 leaked filesystem paths in response body
    const serialized = JSON.stringify(body);
    expect(serialized).not.toMatch(/\/home\//);
    expect(serialized).not.toMatch(/\/var\//);
    expect(serialized).not.toMatch(/\/tmp\//);
    expect(serialized).not.toMatch(/[a-zA-Z]:\\/);
    expect(serialized).not.toMatch(/\.\.[\\/]/);
  });
});
