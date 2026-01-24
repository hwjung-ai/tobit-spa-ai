import { test, expect } from '@playwright/test';

// BASE_URL not used in these tests
const API_BASE_URL = 'http://localhost:8000';

test.describe.serial('RCA Comprehensive Test Suite', () => {
  let testTraceId: string;
  let firstRcaTraceId: string;
  const getRcaData = (body: Record<string, unknown>) =>
    (body?.data as Record<string, unknown> | undefined) ?? body;

  test('Setup: Create test trace with data', async ({ page }) => {
    // Create a sample trace to work with
    const traceResponse = await page.request.post(`${API_BASE_URL}/inspector/traces`, {
      data: {
        trace_id: 'test-rca-trace-' + Date.now(),
        feature: 'test',
        endpoint: '/test',
        method: 'POST',
        ops_mode: 'test',
        question: 'Test question for RCA',
        status: 'success',
        duration_ms: 1000,
        request_payload: { test: true },
        answer: {
          meta: { summary: 'Test answer' },
          blocks: [{ type: 'markdown', content: 'Test' }],
        },
      },
    });

    const body = await traceResponse.json();
    testTraceId = body.data.trace_id || body.trace_id;
    console.log('✅ Test trace created:', testTraceId);
    expect(testTraceId).toBeTruthy();
  });

  test('Test 1: First RCA execution - should create new trace', async ({ page }) => {
    console.log('\n📋 Test 1: First RCA execution');
    console.log('Input trace_id:', testTraceId);

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: testTraceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('Response status:', response.status());
    const body = await response.json();
    const data = getRcaData(body);
    console.log('Response code:', body.code);

    // Check response
    expect(response.ok()).toBeTruthy();
    expect(data).toBeTruthy();
    expect(data.trace_id).toBeTruthy();

    firstRcaTraceId = data.trace_id as string;
    console.log('✅ RCA trace created:', firstRcaTraceId);
    console.log('   Status:', data.status);
    console.log('   Hypotheses:', (data.rca as { total_hypotheses?: number } | undefined)?.total_hypotheses);
  });

  test('Test 2: Verify first RCA trace is in database', async ({ page }) => {
    console.log('\n📋 Test 2: Verify RCA trace in database');
    console.log('Looking for trace:', firstRcaTraceId);

    // Wait for DB persistence
    await page.waitForTimeout(500);

    const response = await page.request.get(`${API_BASE_URL}/inspector/traces/${firstRcaTraceId}`);

    console.log('Response status:', response.status());
    const body = await response.json();
    const data = getRcaData(body);

    expect(response.ok()).toBeTruthy();
    expect(body.data.trace.trace_id).toBe(firstRcaTraceId);
    expect(body.data.trace.feature).toBe('rca');
    console.log('✅ RCA trace found in database');
    console.log('   Question:', body.data.trace.question);
    console.log('   Answer blocks:', body.data.trace.answer.blocks.length);
  });

  test('Test 3: Second RCA execution on same source - should work', async ({ page }) => {
    console.log('\n📋 Test 3: Second RCA execution on same source');
    console.log('Source trace_id:', testTraceId);

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: testTraceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('Response status:', response.status());
    const body = await response.json();
    const data = getRcaData(body);

    if (!response.ok()) {
      console.log('Error:', body.message);
    }

    expect(response.ok()).toBeTruthy();
    expect(data.trace_id).toBeTruthy();
    expect(data.trace_id).not.toBe(firstRcaTraceId); // Should be different

    console.log('✅ Second RCA executed successfully');
    console.log('   New trace_id:', data.trace_id);
    console.log('   (Different from first:', data.trace_id !== firstRcaTraceId, ')');
  });

  test('Test 4: RCA on previous RCA trace - should work', async ({ page }) => {
    console.log('\n📋 Test 4: RCA on previous RCA trace');
    console.log('RCA trace_id:', firstRcaTraceId);

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'single',
        trace_id: firstRcaTraceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('Response status:', response.status());
    const body = await response.json();
    const data = getRcaData(body);

    if (!response.ok()) {
      console.log('Error:', body.message);
      console.log('Full response:', JSON.stringify(body, null, 2));
    }

    expect(response.ok()).toBeTruthy();
    expect(data.trace_id).toBeTruthy();
    console.log('✅ RCA on RCA trace executed successfully');
    console.log('   Source (RCA trace):', firstRcaTraceId);
    console.log('   New trace_id:', data.trace_id);
  });

  test('Test 5: RCA diff mode - compare two traces', async ({ page }) => {
    console.log('\n📋 Test 5: RCA diff mode');

    const response = await page.request.post(`${API_BASE_URL}/ops/rca`, {
      data: {
        mode: 'diff',
        baseline_trace_id: testTraceId,
        candidate_trace_id: firstRcaTraceId,
        options: {
          max_hypotheses: 5,
          include_snippets: true,
          use_llm: false,
        },
      },
    });

    console.log('Response status:', response.status());
    const body = await response.json();
    const data = getRcaData(body);

    if (!response.ok()) {
      console.log('Error:', body.message);
    }

    expect(response.ok()).toBeTruthy();
    expect(data.trace_id).toBeTruthy();
    expect((data.rca as { mode?: string } | undefined)?.mode).toBe('diff');
    expect(((data.rca as { source_traces?: unknown[] } | undefined)?.source_traces || []).length).toBe(2);

    console.log('✅ RCA diff mode executed successfully');
    console.log('   Baseline:', testTraceId);
    console.log('   Candidate:', firstRcaTraceId);
    console.log('   Hypotheses found:', (data.rca as { total_hypotheses?: number } | undefined)?.total_hypotheses);
  });

  test('Test 6: Regression page API check', async ({ page }) => {
    console.log('\n📋 Test 6: Regression page - golden queries');

    const response = await page.request.get(`${API_BASE_URL}/ops/golden-queries`);

    console.log('Response status:', response.status());
    if (response.ok()) {
      const body = await response.json();
      console.log('Golden queries count:', body.data?.queries?.length || 0);
      console.log('✅ Golden queries API accessible');
    } else {
      console.log('⚠️  Golden queries API not available');
      console.log('   This is expected if tb_golden_query table is not initialized');
    }
  });
});
