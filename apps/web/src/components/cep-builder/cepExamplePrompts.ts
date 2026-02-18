import type { ExamplePrompt } from "@/components/copilot/ExamplePrompts";

export const CEP_EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    label: "CPU Alert",
    prompt: "CPU usage over 85% for more than 5 minutes, send Slack alert",
    icon: "⚠️",
  },
  {
    label: "Error Spike",
    prompt: "More than 100 error logs per minute, trigger PagerDuty",
    icon: "🚨",
  },
  {
    label: "Memory Leak",
    prompt: "Memory usage increasing continuously for 10 minutes, send alert",
    icon: "📈",
  },
  {
    label: "Response Time",
    prompt: "Response time p95 exceeds 800ms, create ticket",
    icon: "⏰",
  },
  {
    label: "Cost Alert",
    prompt: "Hourly cost exceeds $50, send email notification",
    icon: "💸",
  },
  {
    label: "Failover",
    prompt: "Service down event, send SMS and Email simultaneously",
    icon: "📢",
  },
];
