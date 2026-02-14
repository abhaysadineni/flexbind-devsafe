import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import Home from './pages/Home';
import Jobs from './pages/Jobs';

type Page = 'home' | 'jobs';

function getPage(): Page {
  const hash = window.location.hash.replace('#', '');
  if (hash.startsWith('jobs')) return 'jobs';
  return 'home';
}

export default function App() {
  const [page, setPage] = useState<Page>(getPage);

  useEffect(() => {
    const handler = () => setPage(getPage());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = (p: Page) => {
    window.location.hash = p === 'home' ? '' : p;
    setPage(p);
  };

  return (
    <Layout page={page} onNavigate={navigate}>
      {page === 'home' ? (
        <Home onJobCreated={() => navigate('jobs')} />
      ) : (
        <Jobs />
      )}
    </Layout>
  );
}
