import { HomeView } from './presentation/pages/home/HomeView'
import './index.css'

function App() {
  return (
    <>
      <HomeView />
      {/* 
        The ClipEditorView would ideally be rendered here or mapped to a router:
        <ClipEditorView onSave={...} onCancel={...} />
      */}
    </>
  )
}

export default App
