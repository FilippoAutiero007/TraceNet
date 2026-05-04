import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import './index.css'
import App from './App.tsx'

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!clerkPubKey && import.meta.env.DEV) {
  console.warn(
    'VITE_CLERK_PUBLISHABLE_KEY is not defined. ClerkProvider will not render. ' +
    'Add VITE_CLERK_PUBLISHABLE_KEY to your .env file.'
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {clerkPubKey ? (
      <ClerkProvider publishableKey={clerkPubKey}>
        <App />
      </ClerkProvider>
    ) : (
      <App />
    )}
  </StrictMode>,
)
