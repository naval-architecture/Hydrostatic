import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Naval Architecture Suite",
  description: "Hull hydrostatic calculation tools",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
