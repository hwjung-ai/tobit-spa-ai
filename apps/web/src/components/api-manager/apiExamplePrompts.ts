import type { ExamplePrompt } from "@/components/copilot/ExamplePrompts";

export const API_EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    label: "CPU Metrics",
    prompt: "Create a GET API to query CPU usage. Endpoint should be /metrics/cpu",
    icon: "📈",
  },
  {
    label: "User List",
    prompt: "Create an API to fetch user list with pagination support",
    icon: "👤",
  },
  {
    label: "Create Order",
    prompt: "Create a POST API for order creation. Required fields: user_id, product_id, quantity",
    icon: "🛒",
  },
  {
    label: "Log Search",
    prompt: "Create an API to search error logs. Need severity and date filters",
    icon: "🔎",
  },
  {
    label: "Statistics",
    prompt: "Create an API to aggregate daily request counts",
    icon: "📊",
  },
  {
    label: "External API",
    prompt: "Create an HTTP API that calls an external weather API and returns the data",
    icon: "🌐",
  },
];
