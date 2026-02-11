import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:3000';

async function testInteractions() {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  const issues = [];

  // Test 1: Navigation flow
  console.log('\n--- Testing Navigation ---');
  await page.goto(BASE_URL);

  const navItems = ['Probes', 'Directives', 'Stars', 'Constellations', 'Runs', 'Launchpad'];
  for (const item of navItems) {
    try {
      await page.click(`text=${item}`);
      await page.waitForTimeout(300);
      const url = page.url();
      console.log(`✓ Nav to ${item}: ${url}`);
    } catch (e) {
      issues.push(`Navigation to ${item} failed: ${e.message}`);
      console.log(`✗ Nav to ${item} failed`);
    }
  }

  // Test 2: Create flows
  console.log('\n--- Testing Create Flows ---');

  // Directive creation
  try {
    await page.goto(`${BASE_URL}/directives/new`);
    await page.waitForTimeout(500);

    // Check for form elements
    const hasNameInput = await page.$('input[name="name"], input[placeholder*="name"], #name');
    const hasSubmit = await page.$('button[type="submit"], button:has-text("Create"), button:has-text("Save")');

    if (!hasNameInput) issues.push('Directive form: Missing name input');
    if (!hasSubmit) issues.push('Directive form: Missing submit button');

    console.log(`✓ Directive form: name=${!!hasNameInput}, submit=${!!hasSubmit}`);
  } catch (e) {
    issues.push(`Directive creation page failed: ${e.message}`);
  }

  // Star creation
  try {
    await page.goto(`${BASE_URL}/stars/new`);
    await page.waitForTimeout(500);

    const hasTypeSelect = await page.$('select, [role="listbox"], [data-testid="type-select"]');
    const hasDirectiveSelect = await page.$('select, [role="listbox"], [data-testid="directive-select"]');

    if (!hasTypeSelect) issues.push('Star form: Missing type selector');

    console.log(`✓ Star form: type=${!!hasTypeSelect}, directive=${!!hasDirectiveSelect}`);
  } catch (e) {
    issues.push(`Star creation page failed: ${e.message}`);
  }

  // Test 3: Keyboard navigation
  console.log('\n--- Testing Keyboard Navigation ---');
  await page.goto(`${BASE_URL}/directives`);

  // Tab through interactive elements
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => {
      const el = document.activeElement;
      return el ? { tag: el.tagName, class: el.className, visible: el.offsetParent !== null } : null;
    });

    if (focused && !focused.visible) {
      issues.push(`Focus on invisible element: ${focused.tag}.${focused.class}`);
    }
  }
  console.log('✓ Tab navigation completed');

  // Test 4: Loading states
  console.log('\n--- Testing Loading States ---');
  await page.goto(`${BASE_URL}/stars`, { waitUntil: 'domcontentloaded' });

  // Check if loading indicator appears
  const hasLoader = await page.$('.spinner, .loading, [data-loading], .skeleton');
  console.log(`  Loading indicator: ${hasLoader ? '✓ Present' : '? Not detected (might be too fast)'}`);

  // Test 5: Error handling
  console.log('\n--- Testing Error States ---');
  // Attempt to visit non-existent detail page
  try {
    await page.goto(`${BASE_URL}/directives/nonexistent-id-12345`);
    await page.waitForTimeout(500);

    const hasError = await page.$('.error, [role="alert"], :has-text("not found"), :has-text("Error")');
    console.log(`  404/Error state: ${hasError ? '✓ Handled' : '✗ No error shown'}`);
    if (!hasError) issues.push('Missing error state for invalid ID');
  } catch (e) {
    console.log(`  404 test: ${e.message}`);
  }

  // Test 6: Focus trap in modals
  console.log('\n--- Testing Modal Focus Trap ---');
  try {
    await page.goto(`${BASE_URL}/directives`);
    await page.waitForTimeout(500);

    // Try to open a delete modal
    const deleteBtn = await page.$('[data-testid="delete-btn"], button:has-text("Delete")');
    if (deleteBtn) {
      await deleteBtn.click();
      await page.waitForTimeout(300);

      // Tab multiple times to see if focus stays in modal
      let focusEscaped = false;
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');
        const focusedElement = await page.evaluate(() => {
          const modal = document.querySelector('[role="dialog"], .modal');
          const activeEl = document.activeElement;
          return modal && activeEl ? modal.contains(activeEl) : true;
        });
        if (!focusedElement) {
          focusEscaped = true;
          break;
        }
      }

      if (focusEscaped) {
        issues.push('Modal focus trap: Focus escaped modal during Tab navigation');
        console.log('✗ Modal focus trap: Focus escaped');
      } else {
        console.log('✓ Modal focus trap: Focus contained (or no modal found)');
      }
    } else {
      console.log('- No delete button found to test modal');
    }
  } catch (e) {
    console.log(`- Modal test error: ${e.message}`);
  }

  // Summary
  console.log('\n--- Interaction Issues Found ---');
  if (issues.length === 0) {
    console.log('✓ No critical issues found');
  } else {
    issues.forEach((issue, i) => console.log(`${i + 1}. ${issue}`));
  }

  await browser.close();
  return issues;
}

testInteractions().catch(console.error);
