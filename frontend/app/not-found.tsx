import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h1 className="text-6xl font-bold text-gray-300">404</h1>
      <h2 className="text-2xl font-medium mt-4 mb-6">Page Not Found</h2>
      <p className="text-gray-600 max-w-md mb-8">
        We couldn't find the page you're looking for. The page might have been moved or deleted.
      </p>
      <Link
        href="/"
        className="bg-black text-white px-6 py-3 rounded-md font-medium hover:bg-gray-800 transition-colors"
      >
        Return Home
      </Link>
    </div>
  );
} 