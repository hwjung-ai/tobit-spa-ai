import { test, expect } from '@playwright/test';

const API_BASE_URL = 'http://localhost:8000';

test.describe('RCA Real Trace Test', () => {
  // Use a real trace ID from the database
  const REAL_TRACE_ID = '6c9dcb5d-8e01-4b7f-b4f1-11b2b6bca1cd';

  test('Get existing trace', async ({ page }) => {
    console.log('\n🔍 Checking if trace exists');
    const response = await page.request.get(`${API_BASE_URL}/inspector/traces/${REAL_TRACE_ID}`);

    console.log('Status:', response.status());
    if (response.ok()) {
      const body = await response.json();
      console.log('✅ Trace found:', REAL_TRACE_ID);
      console.log('   Feature:', body.data.trace.feature);
      console.log('   Status:', body.data.trace.status);
    } else {
      console.log('❌ Trace not found');
    }
  });

  test('First RCA execution', async ({ page }) => {
    console.log('\n🚀 First RCA execution');
    console.log('Source trace:', REAL_TRACE_ID);

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: REAL_TRACE_ID,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('\nResponse:');
    console.log('  Status:', response.status());

    const body = await response.json();
    console.log('  Code:', body.code);
    console.log('  Message:', body.message);

    if (body.data) {
      console.log('  Data:', JSON.stringify(body.data, null, 2));
      console.log('\n✅ RCA completed');
      console.log('  Trace ID:', body.data.trace_id);
      console.log('  Status:', body.data.status);
      console.log('  Hypotheses:', body.data.rca.total_hypotheses);
    } else {
      console.log('  Error - No data in response');
    }

    expect(response.ok()).toBeTruthy();
    expect(body.data).toBeTruthy();
    expect(body.data.trace_id).toBeTruthy();
  });

  test('Second RCA on same source', async ({ page }) => {
    console.log('\n🚀 Second RCA execution on same source');

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: REAL_TRACE_ID,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('\nResponse:');
    console.log('  Status:', response.status());

    const body = await response.json();
    console.log('  Code:', body.code);

    if (body.data) {
      console.log('  ✅ Second RCA succeeded');
      console.log('  Trace ID:', body.data.trace_id);
    } else {
      console.log('  ❌ Error:', body.message);
    }

    expect(response.ok()).toBeTruthy();
    expect(body.data.trace_id).toBeTruthy();
  });

  test('RCA Diff mode', async ({ page }) => {
    console.log('\n🚀 RCA Diff mode test');

    // First create two RCA traces
    const rca1 = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: REAL_TRACE_ID,
        options: { max_hypotheses: 5, include_snippets: true, use_llm: false },
      },
    });

    const body1 = await rca1.json();
    const traceId1 = body1.data.trace_id;

    const rca2 = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: REAL_TRACE_ID,
        options: { max_hypotheses: 5, include_snippets: true, use_llm: false },
      },
    });

    const body2 = await rca2.json();
    const traceId2 = body2.data.trace_id;

    console.log('Created traces:', traceId1, 'and', traceId2);

    // Now run diff mode
    const diffResponse = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'diff',
        baseline_trace_id: traceId1,
        candidate_trace_id: traceId2,
        options: { max_hypotheses: 5, include_snippets: true, use_llm: false },
      },
    });

    console.log('\nDiff mode response:');
    console.log('  Status:', diffResponse.status());

    const diffBody = await diffResponse.json();
    console.log('  Code:', diffBody.code);

    if (diffBody.data) {
      console.log('  ✅ Diff RCA succeeded');
      console.log('  Trace ID:', diffBody.data.trace_id);
      console.log('  Hypotheses:', diffBody.data.rca.total_hypotheses);
    } else {
      console.log('  ❌ Error:', diffBody.message);
    }

    expect(diffResponse.ok()).toBeTruthy();
    expect(diffBody.data.trace_id).toBeTruthy();
  });
});
