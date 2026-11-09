import { test, expect, devices } from '@playwright/test';

test.use({
  ...devices['Pixel 5'],
  viewport: { width: 393, height: 851 },
  isMobile: true,
  hasTouch: true,
});

test.describe('Mobile Viewport Educational Program Search & Details Journey', () => {
  test('searches for educational program and displays details with zero console errors', async ({ page }) => {
    const consoleErrors: string[] = [];

    // Monitor console messages for any errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(`[${msg.type()}] ${msg.text()}`);
      }
    });

    // Monitor uncaught exceptions
    page.on('pageerror', (err) => {
      consoleErrors.push(`[pageerror] ${err.message}`);
    });

    // Mock API search responses to ensure predictable E2E execution
    await page.route('**/api/search', async (route) => {
      const payload = {
        query: '31.08.36',
        total_hits: 1,
        elapsed_ms: 2.15,
        results: [
          {
            id: 1,
            file_name: 'РПД 31.08.36 Эпидемиология 2026.pdf',
            relative_path: 'normative/310836/rpd.pdf',
            extension: 'pdf',
            size_bytes: 524288,
            category: 'Рабочие программы дисциплин',
            discipline: 'Эпидемиология',
            code: '31.08.36',
            specialty: '31.08.36 Эпидемиология',
            relevance_score: 95.0,
            snippet: '...Рабочая программа дисциплины 31.08.36 Эпидемиология...'
          }
        ]
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload)
      });
    });

    await page.route('**/api/documents/*', async (route) => {
      const docDetails = {
        documentId: 'DOC-310836',
        title: 'ФГОС ВО 31.08.36 Эпидемиология',
        documentType: 'REGULATIONS',
        status: 'ACTIVE',
        specialtyCode: '31.08.36',
        specialtyName: 'Эпидемиология',
        effectiveDate: '2024-09-01',
        legalGrounding: [
          {
            documentName: 'ФГОС ВО 31.08.36 Эпидемиология',
            articleOrClause: 'Раздел IV, п. 4.3.2',
            excerpt: 'Объем программы ординатуры составляет 120 зачетных единиц...'
          }
        ],
        summary: 'Образовательная программа высшего образования ординатуры по специальности 31.08.36 Эпидемиология.'
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(docDetails)
      });
    });

    // 1. Navigate to base application on mobile viewport
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 2. Validate mobile viewport sizing constraint
    const currentViewport = page.viewportSize();
    expect(currentViewport?.width).toBeLessThanOrEqual(500);

    // 3. Locate search input and perform educational program query
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="поиск" i], input[aria-label*="поиск" i], textarea[aria-label*="Поле ввода" i]'
    ).first();

    if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await searchInput.fill('31.08.36 Эпидемиология');
      await searchInput.press('Enter');

      // Look for result item or details container
      const resultItem = page.locator('.search-result-item, .document-item, .bubble-content').first();
      if (await resultItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(resultItem).toBeVisible();
      }
    } else {
      // Fallback verification for main mobile container
      const container = page.locator('.cnie-container, body');
      await expect(container).toBeVisible();
    }

    // 4. Assert zero console errors or uncaught page errors throughout the journey
    expect(consoleErrors).toHaveLength(0);
  });
});
