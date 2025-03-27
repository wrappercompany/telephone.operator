"use client";

import Image from 'next/image';
import Link from 'next/link';

interface AppCardProps {
  name: string;
  screenshots: string[];
}

export default function AppCard({ name, screenshots }: AppCardProps) {
  // Get the first screenshot as the thumbnail
  const thumbnail = screenshots.length > 0 ? screenshots[0] : null;
  
  // Format the app name to be more user-friendly
  const formattedName = name
    .replace(/^mobile/, '')  // Remove 'mobile' prefix
    .split(/(?=[A-Z])/).join(' ')  // Add spaces before capital letters
    .replace(/^\w/, c => c.toUpperCase());  // Capitalize first letter
  
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <Link href={`/app/${name}`}>
        <div className="relative h-48 bg-gray-200">
          {thumbnail ? (
            <Image 
              src={thumbnail} 
              alt={`${formattedName} screenshot`} 
              fill 
              className="object-cover"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              No screenshot available
            </div>
          )}
        </div>
        <div className="p-4">
          <h3 className="text-lg font-semibold">{formattedName}</h3>
          <p className="text-gray-500 text-sm mt-1">{screenshots.length} screenshots</p>
        </div>
      </Link>
    </div>
  );
} 