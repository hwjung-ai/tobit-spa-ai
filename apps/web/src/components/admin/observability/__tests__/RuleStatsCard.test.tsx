import { render, screen } from "@testing-library/react";
import RuleStatsCard from "../RuleStatsCard";

// Mock fetch
global.fetch = jest.fn();

describe("RuleStatsCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders loading state", () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {}) // Never resolves
    );

    render(<RuleStatsCard />);
    expect(screen.getByText(/loading rule statistics/i)).toBeInTheDocument();
  });

  it("renders rules after loading", async () => {
    const mockData = {
      data: {
        rules: [
          {
            rule_id: "rule-1",
            rule_name: "CPU Alert",
            is_active: true,
            execution_count: 100,
            error_count: 5,
            error_rate: 0.05,
            avg_duration_ms: 50,
          },
        ],
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<RuleStatsCard />);

    // Wait for the rule name to appear
    const ruleNameElement = await screen.findByText("CPU Alert");
    expect(ruleNameElement).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("handles errors gracefully", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<RuleStatsCard />);

    const errorElement = await screen.findByText(/error/i);
    expect(errorElement).toBeInTheDocument();
  });

  it("displays rule statistics correctly", async () => {
    const mockData = {
      data: {
        rules: [
          {
            rule_id: "rule-1",
            rule_name: "Test Rule",
            is_active: true,
            execution_count: 150,
            error_count: 10,
            error_rate: 0.067,
            avg_duration_ms: 45.5,
          },
        ],
      },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<RuleStatsCard />);

    const execCount = await screen.findByText("150 executions");
    expect(execCount).toBeInTheDocument();
  });
});
