import { render, screen, waitFor } from "@testing-library/react";
import SystemHealthChart from "../SystemHealthChart";

// Mock fetch
global.fetch = jest.fn();

describe("SystemHealthChart", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it("renders loading state initially", () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {}) // Never resolves
    );

    render(<SystemHealthChart />);
    expect(screen.getByText(/loading system health/i)).toBeInTheDocument();
  });

  it("displays system statistics", async () => {
    const mockStats = {
      data: {
        stats: {
          total_rules: 10,
          active_rules: 8,
          inactive_rules: 2,
          today_execution_count: 500,
          today_error_count: 10,
          today_error_rate: 0.02,
          today_avg_duration_ms: 45.5,
          last_24h_execution_count: 1200,
          timestamp: "2024-02-06T00:00:00Z",
        },
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockStats,
    });

    render(<SystemHealthChart />);

    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument(); // total rules
    });
  });

  it("shows healthy status for low error rate", async () => {
    const mockStats = {
      data: {
        stats: {
          total_rules: 10,
          active_rules: 8,
          inactive_rules: 2,
          today_execution_count: 500,
          today_error_count: 5,
          today_error_rate: 0.01,
          today_avg_duration_ms: 45,
          last_24h_execution_count: 1200,
          timestamp: "2024-02-06T00:00:00Z",
        },
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockStats,
    });

    render(<SystemHealthChart />);

    await waitFor(() => {
      expect(screen.getByText(/Healthy/i)).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<SystemHealthChart />);

    const errorElement = await screen.findByText(/error/i);
    expect(errorElement).toBeInTheDocument();
  });
});
