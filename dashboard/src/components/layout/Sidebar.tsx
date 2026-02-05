'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  PieChart,
  ArrowLeftRight,
  CheckSquare,
  FileText,
  Settings,
  ChevronDown,
  Building2,
} from 'lucide-react';
import { cn, ENTITIES } from '@/lib/utils';
import { useState } from 'react';

interface SidebarProps {
  selectedEntity: string | null;
  onEntityChange: (entity: string | null) => void;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Budget', href: '/budget', icon: PieChart },
  { name: 'Transactions', href: '/transactions', icon: ArrowLeftRight },
  { name: 'Approvals', href: '/approvals', icon: CheckSquare },
  { name: 'Fund Requests', href: '/fund-requests', icon: FileText },
];

export function Sidebar({ selectedEntity, onEntityChange }: SidebarProps) {
  const pathname = usePathname();
  const [entityDropdownOpen, setEntityDropdownOpen] = useState(false);

  const selectedEntityName = selectedEntity
    ? ENTITIES.find((e) => e.code === selectedEntity)?.name || selectedEntity
    : 'All Entities';

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[var(--sidebar-width)] border-r border-navy-200/50 bg-white">
      {/* Logo */}
      <div className="flex h-[var(--header-height)] items-center border-b border-navy-100 px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy-900">
            <span className="font-display text-lg text-white">B</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-navy-900">BETRNK</h1>
            <p className="text-xs text-navy-500">Accounting</p>
          </div>
        </div>
      </div>

      {/* Entity Selector */}
      <div className="border-b border-navy-100 p-4">
        <div className="relative">
          <button
            onClick={() => setEntityDropdownOpen(!entityDropdownOpen)}
            className="flex w-full items-center justify-between rounded-lg border border-navy-200 bg-navy-50/50 px-3 py-2.5 text-left transition-colors hover:bg-navy-100/50"
          >
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-navy-500" />
              <span className="text-sm font-medium text-navy-700">
                {selectedEntityName}
              </span>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-navy-400 transition-transform',
                entityDropdownOpen && 'rotate-180'
              )}
            />
          </button>

          {entityDropdownOpen && (
            <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-navy-200 bg-white py-1 shadow-float">
              <button
                onClick={() => {
                  onEntityChange(null);
                  setEntityDropdownOpen(false);
                }}
                className={cn(
                  'flex w-full items-center px-3 py-2 text-left text-sm transition-colors',
                  !selectedEntity
                    ? 'bg-navy-50 text-navy-900 font-medium'
                    : 'text-navy-600 hover:bg-navy-50'
                )}
              >
                All Entities
              </button>
              {ENTITIES.map((entity) => (
                <button
                  key={entity.code}
                  onClick={() => {
                    onEntityChange(entity.code);
                    setEntityDropdownOpen(false);
                  }}
                  className={cn(
                    'flex w-full items-center px-3 py-2 text-left text-sm transition-colors',
                    selectedEntity === entity.code
                      ? 'bg-navy-50 text-navy-900 font-medium'
                      : 'text-navy-600 hover:bg-navy-50'
                  )}
                >
                  {entity.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4">
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-navy-400">
          Menu
        </p>
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                isActive
                  ? 'bg-navy-900 text-white shadow-sm'
                  : 'text-navy-600 hover:bg-navy-100 hover:text-navy-900'
              )}
            >
              <item.icon className="h-[18px] w-[18px]" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-navy-100 p-4">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-navy-600 transition-colors hover:bg-navy-100 hover:text-navy-900"
        >
          <Settings className="h-[18px] w-[18px]" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
