import { useAuth } from '../context/AuthContext';
import { LogOut } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Home() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white">
      <header className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 shadow">
        <h1 className="text-xl font-bold">SynapseLM</h1>
        <div className="flex items-center gap-4">
          <span>Welcome, {user?.username}</span>
          <button 
            onClick={logout}
            className="flex items-center gap-2 px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      </header>
      
      <main className="p-8 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
        <div className="grid gap-4 md:grid-cols-2 mb-8">
          <Link to="/teams" className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md border dark:border-gray-700 block">
            <h3 className="text-xl font-semibold text-blue-600">My Teams</h3>
            <p className="text-sm mt-2">Manage your teams and collaborate</p>
          </Link>
          <Link to="/invitations" className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md border dark:border-gray-700 block">
            <h3 className="text-xl font-semibold text-green-600">Pending Invitations</h3>
            <p className="text-sm mt-2">View and accept team invites</p>
          </Link>
        </div>

        <div className="mt-4 p-4 border dark:border-gray-700 rounded bg-white dark:bg-gray-800">
          <pre className="text-sm">
            {JSON.stringify(user, null, 2)}
          </pre>
        </div>
      </main>
    </div>
  );
}
