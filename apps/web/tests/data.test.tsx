"use client";

import { render, screen } from "@testing-library/react";
import DataExplorerPage from "@app/data/page";

describe("DataExplorerPage", () => {
  it("renders header and tabs", () => {
    render(<DataExplorerPage />);
    expect(screen.getByText("Data Explorer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Postgres/i })).toBeInTheDocument();
  });
});
