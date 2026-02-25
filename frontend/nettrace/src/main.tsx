import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import './index.css'
import App from './App.tsx'
import { LanguageProvider } from './context/LanguageContext'

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

const root = createRoot(document.getElementById('root')!)

root.render(
  <StrictMode>
    <LanguageProvider>
      {clerkPubKey ? (
        <ClerkProvider publishableKey={clerkPubKey}>
          <App />
        </ClerkProvider>
      ) : (
        <App />
      )}
    </LanguageProvider>
  </StrictMode>,
)
