'use client';

import { Bell, Search, User } from 'lucide-react';
import { useState } from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-[var(--header-height)] items-center justify-between border-b border-navy-100 bg-white/80 px-6 backdrop-blur-lg">
      <div>
        <h1 className="text-xl font-semibold text-navy-900">{title}</h1>
        {subtitle && (
          <p className="text-sm text-navy-500">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative">
          {searchOpen ? (
            <input
              type="text"
              placeholder="Search..."
              className="input w-64 pr-10"
              autoFocus
              onBlur={() => setSearchOpen(false)}
            />
          ) : (
            <button
              onClick={() => setSearchOpen(true)}
              className="btn btn-ghost p-2"
            >
              <Search className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Notifications */}
        <button className="btn btn-ghost relative p-2">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>

        {/* User */}
        <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-navy-100">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-200">
            <User className="h-4 w-4 text-navy-600" />
          </div>
          <span className="text-sm font-medium text-navy-700">Admin</span>
        </button>
      </div>
    </header>
  );
}
