import { expect, test } from '@playwright/test';

test('actual API fixture shows honest fleet counts and model provenance', async ({page}, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Overview'})).toBeVisible();
  await expect(page.getByText('High-risk drives',{exact:true})).toBeVisible();
  await expect(page.getByText('No high-risk drives found.')).toBeVisible();
  await page.getByRole('link',{name:'View all drives'}).click();
  await expect(page.getByText('SYNTHETIC SOFTWARE FIXTURE').first()).toBeVisible();
  await page.getByRole('link',{name:'SYNTHETIC-low',exact:true}).click();
  await page.waitForURL('**/drives/SYNTHETIC-low');
  await expect(page.getByText('synthetic-software-fixture-v1',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Top Reason Codes'})).toBeVisible();
  await expect(page.getByText(/Largest linear log-odds terms/)).toBeVisible();
  await expect(page.locator('body')).not.toContainText('obsolete-synthetic-fixture');
  // Let the chart's entrance animation complete before recording visual evidence.
  await page.waitForTimeout(2000);
  if(testInfo.project.name==='desktop') await page.screenshot({path:'../../docs/media/current/synthetic-drive.png',fullPage:true});
});

test('unscored drive has no fabricated low-risk badge', async ({page}) => {
  await page.goto('/drives/SYNTHETIC-stale');
  await expect(page.getByText('UNSCORED Risk')).toBeVisible();
  await expect(page.getByRole('heading',{name:'No risk history'})).toBeVisible();
});
