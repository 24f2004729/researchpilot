import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ResearchPilot — Evidence-Grounded AI Research Assistant',
  description: 'Multi-document question answering with verifiable source citations, hybrid search, and honest abstention.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 flex flex-col font-sans antialiased text-slate-900">
        {children}
      </body>
    </html>
  );
}
