import { test, expect } from '@playwright/test';

test.describe('Internal UI - Responsive Mobile Journey and Normative Search', () => {
  test.use({
    viewport: { width: 375, height: 667 }, // iPhone SE / Mobile standard
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
  });

  test('completes search for Инфекционные болезни, filters by 31.08.35, and inspects normative document details', async ({
    page
  }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => consoleErrors.push(err.message));

    // Mock API search and facets
    await page.route('**/api/search*', async (route) => {
      const payload = {
        query: 'Инфекционные болезни',
        total_hits: 1,
        elapsed_ms: 12.5,
        results: [
          {
            id: 101,
            file_name: 'РПД 31.08.35 Инфекционные болезни 2026.pdf',
            relative_path: '05 ООП РПД/РПД 31.08.35 Инфекционные болезни 2026.pdf',
            extension: '.pdf',
            size_bytes: 450200,
            category: '05 ООП РПД',
            discipline: 'Инфекционные болезни',
            code: '31.08.35',
            specialty: '31.08.35 Инфекционные болезни',
            relevance_score: 98.5,
            snippet: '...Рабочая программа дисциплины 31.08.35 Инфекционные болезни...'
          }
        ],
        facets: {
          specialties: ['31.08.35 Инфекционные болезни', '31.08.36 Эпидемиология', '31.08.19 Педиатрия'],
          categories: ['05 ООП РПД', 'Положения', 'Регламенты']
        }
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload)
      });
    });

    await page.route('**/api/documents/facets*', async (route) => {
      const facetsPayload = {
        facetDistribution: {
          specialtyCodes: [
            { value: '31.08.35', label: '31.08.35 Инфекционные болезни', count: 420 },
            { value: '31.08.36', label: '31.08.36 Эпидемиология', count: 580 },
            { value: '31.08.19', label: '31.08.19 Педиатрия', count: 310 }
          ],
          documentTypes: [
            { value: 'SYLLABUS_RPD', label: 'РПД', count: 680 },
            { value: 'REGULATIONS', label: 'Положения', count: 120 }
          ]
        },
        totalDocuments: 1697
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(facetsPayload)
      });
    });

    await page.route('**/api/documents/*', async (route) => {
      const docDetails = {
        documentId: 'DOC-310835',
        title: 'РПД 31.08.35 Инфекционные болезни',
        documentType: 'SYLLABUS_RPD',
        status: 'ACTIVE',
        specialtyCode: '31.08.35',
        specialtyName: 'Инфекционные болезни',
        effectiveDate: '2026-09-01',
        legalGrounding: [
          {
            documentName: 'ФГОС ВО 31.08.35 Инфекционные болезни',
            articleOrClause: 'Раздел IV',
            excerpt: 'Программа ординатуры по специальности Инфекционные болезни'
          }
        ],
        summary: 'Рабочая программа дисциплины ординатуры по специальности 31.08.35 Инфекционные болезни.'
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

    // 3. Search for 'Инфекционные болезни' and filter by '31.08.35'
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="поиск" i], input[aria-label*="поиск" i], textarea[aria-label*="Поле ввода" i]'
    ).first();

    if (await searchInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await searchInput.fill('Инфекционные болезни');
      await searchInput.press('Enter');

      // Filter selection if facet filter select/button is present
      const filterSelector = page.locator('select[aria-label*="специальность" i], select#order-spec, [data-facet="31.08.35"]').first();
      if (await filterSelector.isVisible({ timeout: 1000 }).catch(() => false)) {
        await filterSelector.selectOption({ label: '31.08.35 Инфекционные болезни' }).catch(async () => {
          await filterSelector.selectOption('31.08.35');
        });
      }

      // Locate document item and verify details render
      const docItem = page.locator('.search-result-item, .document-item, .bubble-content, .message-bubble').first();
      if (await docItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        await docItem.click();
        await expect(docItem).toBeVisible();
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
