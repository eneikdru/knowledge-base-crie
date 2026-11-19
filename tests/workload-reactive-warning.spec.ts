import { test, expect } from '@playwright/test';

test.describe('Workload Calculator UI Reactive Warnings', () => {
  test('displays dynamic overload badge with correct excess value when 950 total hours are entered', async ({ page }) => {
    // 1. Navigate to the application
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 2. Switch to Workload tab
    const workloadTabBtn = page.locator('#tab-btn-workload, button:has-text("Нагрузка")');
    await expect(workloadTabBtn).toBeVisible({ timeout: 5000 });
    await workloadTabBtn.click();

    // 3. Confirm workload section is active
    const workloadPanel = page.locator('#tabpanel-workload, .workload-section');
    await expect(workloadPanel).toBeVisible();

    // 4. Fill in hours totaling 950 hours (e.g. 250 + 300 + 250 + 100 + 50 = 950)
    // Default inputs: lectures=120, seminars=280, practice=320, supervision=60, gek=40 (sum=820)
    const lecturesInput = page.locator('#hours-lecture');
    const seminarsInput = page.locator('#hours-seminar');
    const practiceInput = page.locator('#hours-practice');
    const postgraduateInput = page.locator('#hours-postgraduate');
    const gekInput = page.locator('#hours-gek');

    await lecturesInput.fill('250');
    await seminarsInput.fill('300');
    await practiceInput.fill('250');
    await postgraduateInput.fill('100');
    await gekInput.fill('50');

    // 5. Total hours should reactively equal 950 ч
    const totalHoursEl = page.locator('.metric-value:has-text("950 ч"), .metric-box:has-text("950")');
    await expect(totalHoursEl).toBeVisible();

    // 6. Overload alert banner dynamically appears
    const overloadAlert = page.locator('.alert-overload, [role="alert"]:has-text("Превышение нормы")');
    await expect(overloadAlert).toBeVisible();

    // 7. Verify excess hours text (950 - 900 ceiling = 50 ч)
    await expect(overloadAlert).toContainText('50 ч');

    // 8. Overload status badge dynamically displays 'Перегрузка' and '+50 ч сверх потолка'
    const overloadBadge = page.locator('.status-badge.badge-danger, .status-badge:has-text("Перегрузка")');
    await expect(overloadBadge).toBeVisible();
    await expect(overloadBadge).toHaveText('Перегрузка');

    const excessBadgeSub = page.locator('.metric-sub:has-text("+50 ч")');
    await expect(excessBadgeSub).toBeVisible();
  });
});
