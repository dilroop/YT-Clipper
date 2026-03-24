import { createRoot } from 'react-dom/client'
import './assets/common.css'
import './assets/style.css'
import './assets/home.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <App />,
)
