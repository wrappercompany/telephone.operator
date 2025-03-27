import Link from 'next/link';

export default function Header() {
  return (
    <header className="bg-black text-white py-4">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-xl font-bold">
            App Screenshots Gallery
          </Link>
          
          <nav className="hidden md:flex space-x-6">
            <Link href="/" className="hover:text-gray-300">
              Home
            </Link>
            <Link href="/apps" className="hover:text-gray-300">
              All Apps
            </Link>
          </nav>
          
          <div className="flex items-center">
            <button className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-md text-sm">
              Search
            </button>
          </div>
        </div>
      </div>
    </header>
  );
} 