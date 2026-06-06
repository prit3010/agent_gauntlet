import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Agent Gauntlet",
  description: "Harness optimization dashboard for AI agents"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
