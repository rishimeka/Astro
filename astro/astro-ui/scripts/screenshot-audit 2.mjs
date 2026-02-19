import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:3000';
const OUTPUT_DIR = './ux-audit-screenshots';

// All routes to capture
const ROUTES = [
  { path: '/', name: 'dashboard' },
  { path: '/probes', name: 'probes-list' },
  { path: '/directives', name: 'directives-list' },
  { path: '/directives/new', name: 'directives-new' },
  { path: '/stars', name: 'stars-list' },
  { path: '/stars/new', name: 'stars-new' },
  { path: '/constellations', name: 'constellations-list' },
  { path: '/constellations/new', name: 'constellations-new' },
  { path: '/runs', name: 'runs-list' },
  { path: '/launchpad', name: 'launchpad' },
];

// Viewports to test
const VIEWPORTS = [
  { width: 1440, height: 900, name: 'desktop' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 375, height: 812, name: 'mobile' },
];

async function captureScreenshots() {
  // Clean output directory
  if (fs.existsSync(OUTPUT_DIR)) {
    fs.rmSync(OUTPUT_DIR, { recursive: true });
  }
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Enable dark color scheme
  await page.emulateMedia({ colorScheme: 'dark' });

  const results = [];

  for (const route of ROUTES) {
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      const filename = `${route.name}-${viewport.name}.png`;
      const filepath = path.join(OUTPUT_DIR, filename);

      try {
        await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'networkidle', timeout: 10000 });

        // Wait for any loading states to complete
        await page.waitForTimeout(500);

        // Take full page screenshot
        await page.screenshot({ path: filepath, fullPage: true });

        results.push({ route: route.path, viewport: viewport.name, status: 'captured', file: filename });
        console.log(`✓ ${filename}`);
      } catch (error) {
        results.push({ route: route.path, viewport: viewport.name, status: 'failed', error: error.message });
        console.log(`✗ ${filename}: ${error.message}`);
      }
    }
  }

  // Capture specific states
  console.log('\nCapturing component states...');

  // Empty state
  await page.setViewportSize({ width: 1440, height: 900 });

  // Modal state (if applicable)
  try {
    await page.goto(`${BASE_URL}/directives`, { waitUntil: 'networkidle' });
    // Try to trigger a delete modal if there's data
    const deleteBtn = await page.$('[data-testid="delete-btn"], .delete-btn, button:has-text("Delete")');
    if (deleteBtn) {
      await deleteBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'modal-delete-confirm.png') });
      console.log('✓ modal-delete-confirm.png');
    }
  } catch (e) {
    console.log('- Skipped modal capture');
  }

  // Hover states
  try {
    await page.goto(`${BASE_URL}/stars`, { waitUntil: 'networkidle' });
    const row = await page.$('tr[data-clickable], .data-table-row, tbody tr');
    if (row) {
      await row.hover();
      await page.screenshot({ path: path.join(OUTPUT_DIR, 'table-row-hover.png') });
      console.log('✓ table-row-hover.png');
    }
  } catch (e) {
    console.log('- Skipped hover capture');
  }

  await browser.close();

  // Write results manifest
  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'manifest.json'),
    JSON.stringify(results, null, 2)
  );

  console.log(`\n✓ Screenshots saved to ${OUTPUT_DIR}/`);
  console.log(`  Total: ${results.filter(r => r.status === 'captured').length} captured, ${results.filter(r => r.status === 'failed').length} failed`);
}

captureScreenshots().catch(console.error);
