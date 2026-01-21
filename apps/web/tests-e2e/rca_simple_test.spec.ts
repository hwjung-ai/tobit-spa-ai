import { test, expect } from '@playwright/test';

// BASE_URL not used in these tests

test.describe('RCA Simple Test', () => {
  test('RCA API should return valid trace_id', async ({ page }) => {
    // Make a direct API call to test RCA endpoint
    const traceId = '6c9dcb5d-8e01-4b7f-b4f1-11b2b6bca1cd'; // Real trace from logs

    const response = await page.request.post(`http://localhost:8000/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: traceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('Response status:', response.status());
    const responseBody = await response.json();
    console.log('Response body:', JSON.stringify(responseBody, null, 2));

    // Check response structure
    expect(response.ok()).toBeTruthy();
    expect(responseBody).toHaveProperty('data');
    expect(responseBody.data).toHaveProperty('trace_id');
    expect(responseBody.data.trace_id).toBeTruthy();
    expect(typeof responseBody.data.trace_id).toBe('string');

    console.log('✅ RCA API returned valid trace_id:', responseBody.data.trace_id);
  });

  test('RCA trace should be retrievable', async ({ page }) => {
    const traceId = '6c9dcb5d-8e01-4b7f-b4f1-11b2b6bca1cd';

    // Run RCA
    const rca_response = await page.request.post(`http://localhost:8000/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: traceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    const rca_body = await rca_response.json();
    const rca_trace_id = rca_body.data.trace_id;

    console.log('Created RCA trace:', rca_trace_id);

    // Wait a moment for database to persist
    await page.waitForTimeout(1000);

    // Try to retrieve the RCA trace
    const trace_response = await page.request.get(`http://localhost:8000/inspector/traces/${rca_trace_id}`);

    console.log('Trace fetch response status:', trace_response.status());
    const trace_body = await trace_response.json();
    console.log('Trace body:', JSON.stringify(trace_body, null, 2));

    expect(trace_response.ok()).toBeTruthy();
    expect(trace_body).toHaveProperty('data');
    expect(trace_body.data).toHaveProperty('trace');
    expect(trace_body.data.trace).toHaveProperty('trace_id');
    expect(trace_body.data.trace.trace_id).toBe(rca_trace_id);

    console.log('✅ RCA trace retrieved successfully');
  });
});
