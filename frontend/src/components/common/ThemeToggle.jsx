import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';

const ThemeToggle = () => {
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem('solvera_theme');
    return stored ? stored === 'dark' : true; // default dark
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark-mode');
      root.classList.remove('light-mode');
      localStorage.setItem('solvera_theme', 'dark');
    } else {
      root.classList.add('light-mode');
      root.classList.remove('dark-mode');
      localStorage.setItem('solvera_theme', 'light');
    }
  }, [isDark]);

  // Apply stored theme on first load
  useEffect(() => {
    const stored = localStorage.getItem('solvera_theme');
    if (stored === 'light') {
      document.documentElement.classList.add('light-mode');
      document.documentElement.classList.remove('dark-mode');
    } else {
      document.documentElement.classList.add('dark-mode');
      document.documentElement.classList.remove('light-mode');
    }
  }, []);

  return (
    <button
      onClick={() => setIsDark((d) => !d)}
      className="theme-toggle-btn"
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-label="Toggle theme"
    >
      <div className={`theme-toggle-track ${isDark ? 'theme-toggle-track--dark' : 'theme-toggle-track--light'}`}>
        <div className={`theme-toggle-thumb ${isDark ? 'theme-toggle-thumb--dark' : 'theme-toggle-thumb--light'}`}>
          {isDark ? <Moon size={12} /> : <Sun size={12} />}
        </div>
      </div>
    </button>
  );
};

export default ThemeToggle;
