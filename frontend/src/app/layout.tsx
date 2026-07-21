import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'OpsAssistantAI - Incident Analysis',
  description: 'AI-powered Production Incident Root Cause Analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

