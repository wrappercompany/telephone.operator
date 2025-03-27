"use client";

import Image from 'next/image';
import Link from 'next/link';
import { useState } from 'react';

interface AppCardProps {
  name: string;
  screenshots: string[];
}

export default function AppCard({ name, screenshots }: AppCardProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // Format the app name to be more user-friendly
  const formattedName = name
    .replace(/^mobile/, '')  // Remove 'mobile' prefix
    .split(/(?=[A-Z])/).join(' ')  // Add spaces before capital letters
    .replace(/^\w/, c => c.toUpperCase());  // Capitalize first letter
  
  const handleNextImage = (e: React.MouseEvent) => {
    e.preventDefault();
    setCurrentIndex((prev) => (prev + 1) % screenshots.length);
  };

  return (
    <Link href={`/app/${name}`} className="block group">
      <div className="rounded-xl p-8 px-18 relative">
        
        {/* Phone frame with screenshot */}
        <div className="relative aspect-[9/19] mx-auto max-w-xs mb-6">
          <div className="absolute inset-0 bg-black rounded-[20px] overflow-hidden">
            {screenshots.length > 0 ? (
              <Image 
                src={screenshots[currentIndex]} 
                alt={`${formattedName} screenshot ${currentIndex + 1}`} 
                fill 
                className="object-cover"
                sizes="(max-width: 640px) 80vw, 300px"
                priority
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400">
                No screenshot available
              </div>
            )}
          </div>
          
        </div>
        
        {/* App info */}
        <div className="flex items-center mt-8">

          <div>
            <h3 className="text-lg font-bold text-black">{formattedName}</h3>
          </div>
        </div>
      </div>
    </Link>
  );
} 