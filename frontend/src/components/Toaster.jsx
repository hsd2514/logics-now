import React, { createContext, useContext, useState, useCallback } from 'react'
import { X, CheckCircle2, AlertTriangle, Info, XCircle } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />,
  error:   <XCircle      className="h-4 w-4 text-red-500   flex-shrink-0" />,
  warning: <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0" />,
  info:    <Info          className="h-4 w-4 text-blue-500  flex-shrink-0" />,
}

const BG = {
  success: 'border-green-200  bg-green-50  dark:border-green-800  dark:bg-green-950',
  error:   'border-red-200    bg-red-50    dark:border-red-800    dark:bg-red-950',
  warning: 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950',
  info:    'border-blue-200   bg-blue-50   dark:border-blue-800   dark:bg-blue-950',
}

let _id = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const toast = useCallback(({ title, description, type = 'info', duration = 4000 }) => {
    const id = ++_id
    setToasts(prev => [...prev, { id, title, description, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration)
  }, [])

  const dismiss = useCallback(id => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`flex items-start gap-3 border rounded-lg p-3 shadow-lg text-sm animate-in slide-in-from-right-4 ${BG[t.type]}`}
          >
            {ICONS[t.type]}
            <div className="flex-1 min-w-0">
              {t.title && <p className="font-semibold">{t.title}</p>}
              {t.description && <p className="text-muted-foreground text-xs mt-0.5">{t.description}</p>}
            </div>
            <button onClick={() => dismiss(t.id)} className="text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
