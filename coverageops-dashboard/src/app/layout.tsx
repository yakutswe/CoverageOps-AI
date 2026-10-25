import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CoverageOps AI | Agent Control Center",
  description: "Evidence-first insurance workflow control center (synthetic demo)",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
