/**
 * Next.js API Route to proxy SSE (Server-Sent Events) connections
 * This routes browser SSE requests through Next.js (port 3000) to the backend (port 8000)
 * to avoid firewall issues when direct port 8000 access is blocked.
 */

import { NextRequest, NextResponse } from "next/server";

// API Base URL configuration with fallback
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    // Get the original URL path after /sse-proxy
    const { searchParams } = new URL(request.url);
    const forwardParams = new URLSearchParams(searchParams);
    const token = forwardParams.get("token");
    if (token) {
      forwardParams.delete("token");
    }
    const pathname = request.nextUrl.pathname.replace(/^\/sse-proxy/, "");

    const queryString = forwardParams.toString();

    // Build the target backend URL
    const targetUrl = new URL(
      `${pathname}${queryString ? `?${queryString}` : ""}`,
      API_BASE_URL
    );

    console.log(`[SSE Proxy] Forwarding to: ${targetUrl.toString()}`);

    // Prepare headers to forward (exclude hop-by-hop headers)
    const headers = new Headers();
    request.headers.forEach((value, key) => {
      // Skip headers that should not be forwarded
      if (
        key.toLowerCase() === 'host' ||
        key.toLowerCase() === 'connection' ||
        key.toLowerCase() === 'keep-alive' ||
        key.toLowerCase() === 'transfer-encoding' ||
        key.toLowerCase() === 'upgrade'
      ) {
        return;
      }
      headers.set(key, value);
    });
    if (token && !headers.has("authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    // Forward the request to the backend with caching disabled
    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers,
      cache: 'no-store', // Crucial for SSE to avoid buffering/caching
    });

    console.log(`[SSE Proxy] Backend responded with status: ${response.status}`);

    // Create a readable stream from the backend response
    const reader = response.body?.getReader();
    if (!reader) {
      return NextResponse.json(
        { error: 'No response body from backend' },
        { status: 500 }
      );
    }

    // Create a new response with the stream
    const stream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            controller.enqueue(value);
          }
          controller.close();
        } catch (error) {
          console.error('[SSE Proxy] Stream error:', error);
          controller.error(error);
        }
      },
    });

    // Copy SSE headers from backend response
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(stream, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('[SSE Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Failed to proxy SSE request' },
      { status: 500 }
    );
  }
}
