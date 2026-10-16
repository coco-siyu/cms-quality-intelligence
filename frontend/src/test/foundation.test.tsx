import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FoundationPage } from "../app/FoundationPage";

describe("frontend foundation", () => {
  it("renders the application identity and checkpoint status", () => {
    render(<FoundationPage />);

    expect(
      screen.getByRole("heading", { name: "CMS Quality Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/application foundation is ready/i)).toBeInTheDocument();
  });
});
