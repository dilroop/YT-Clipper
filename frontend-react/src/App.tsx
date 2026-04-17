import { Routes, Route } from 'react-router-dom'
import { HomeView } from './presentation/pages/home/HomeView'
import { GalleryPage } from './presentation/pages/gallery/GalleryPage'
import { ClipDetailsPage } from './presentation/pages/gallery/ClipDetailsPage'
import { StoryMakerPage } from './presentation/pages/storymaker/StoryMakerPage'
import './index.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeView />} />
      <Route path="/gallery" element={<GalleryPage />} />
      <Route path="/gallery/:project/:format/:filename" element={<ClipDetailsPage />} />
      <Route path="/story-maker" element={<StoryMakerPage />} />
    </Routes>
  )
}

export default App
