'use client';

import './globals.css';
import { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);

  return (
    <html lang="en">
      <head>
        <title>BETRNK Accounting Dashboard</title>
        <meta name="description" content="Accounting automation dashboard for BK Keyforce / BETRNK Group" />
      </head>
      <body>
        <Sidebar
          selectedEntity={selectedEntity}
          onEntityChange={setSelectedEntity}
        />
        <main className="ml-[var(--sidebar-width)] min-h-screen bg-pattern">
          {children}
        </main>
      </body>
    </html>
  );
}
