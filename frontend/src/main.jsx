import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
// Hapus salah satu jika isinya duplikat, atau pastikan jalurnya benar
//import './styles/global.css' 

const rootElement = document.getElementById('root');

if (!rootElement) {
  console.error("Gagal menemukan elemen root. Pastikan <div id='root'></div> ada di index.html");
} else {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>
    </React.StrictMode>
  )
}