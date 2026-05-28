'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { StageStatus } from '@/lib/store'
import clsx from 'clsx'

interface Props {
  title: string
  subtitle: string
  icon: string
  status: StageStatus
  progress: number
  message: string
  children?: React.ReactNode
}

const statusStyles: Record<StageStatus, string> = {
  idle:   'border-border bg-white',
  active: 'border-brand-200 bg-brand-50/30 shadow-[0_0_0_3px_theme(colors.brand.50)]',
  done:   'border-emerald-200 bg-white',
  error:  'border-red-200 bg-red-50/30',
}

const badgeStyles: Record<StageStatus, string> = {
  idle:   'bg-surface-1 text-gray-400 border-border',
  active: 'bg-brand-50 text-brand-500 border-brand-200 animate-pulse',
  done:   'bg-emerald-50 text-emerald-600 border-emerald-200',
  error:  'bg-red-50 text-red-500 border-red-200',
}

const badgeLabels: Record<StageStatus, string> = {
  idle: 'idle', active: 'processing', done: 'done', error: 'error',
}

export default function StageCard({ title, subtitle, icon, status, progress, message, children }: Props) {
  const [open, setOpen] = useState(false)

  // Auto-open when active
  if (status === 'active' && !open) setOpen(true)

  return (
    <motion.div
      layout
      className={clsx('rounded-2xl border transition-all duration-300', statusStyles[status])}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-surface-1/50 transition-colors rounded-2xl"
      >
        <div className={clsx(
          'w-9 h-9 rounded-xl flex items-center justify-center text-base border transition-colors',
          status === 'active' ? 'bg-brand-50 border-brand-200' :
          status === 'done'   ? 'bg-emerald-50 border-emerald-200' :
          'bg-surface-1 border-border'
        )}>
          {icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">{title}</div>
          <div className="text-xs font-mono text-gray-400 mt-0.5">{subtitle}</div>
        </div>

        <div className={clsx('text-[10px] font-mono px-2.5 py-1 rounded-full border', badgeStyles[status])}>
          {badgeLabels[status]}
        </div>

        <ChevronDown
          size={14}
          className={clsx('text-gray-400 transition-transform flex-shrink-0', open && 'rotate-180')}
        />
      </button>

      {/* Progress bar */}
      {(status === 'active' || status === 'done') && (
        <div className="mx-5 mb-1 h-0.5 bg-surface-2 rounded-full overflow-hidden">
          <motion.div
            className={clsx('h-full rounded-full', status === 'done' ? 'bg-emerald-400' : 'bg-brand-500')}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      )}

      {/* Status message */}
      {message && (status === 'active' || status === 'done') && (
        <div className="mx-5 mb-3 text-xs font-mono text-gray-400">{message}</div>
      )}

      {/* Body */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-2 border-t border-border">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
