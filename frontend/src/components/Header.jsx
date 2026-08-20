import React from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <nav className="bg-slate-900 text-white p-4 shadow-lg sticky top-0 z-50">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-2xl font-bold tracking-tighter text-blue-400">
          OUTFIT<span className="text-white">AR</span>
        </Link>
        <div className="space-x-6">
          <Link to="/" className="hover:text-blue-400 transition">Registrasi</Link>
          <Link to="/ar-tryon" className="hover:text-blue-400 transition">Virtual Try-On</Link>
        </div>
      </div>
    </nav>
  );
};

export default Header;