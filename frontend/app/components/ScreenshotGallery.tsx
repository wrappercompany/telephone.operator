"use client";

import { useState } from 'react';
import Image from 'next/image';

interface ScreenshotGalleryProps {
  screenshots: string[];
  appName: string;
}

export default function ScreenshotGallery({ screenshots, appName }: ScreenshotGalleryProps) {
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(
    screenshots.length > 0 ? screenshots[0] : null
  );

  // Format the app name to be more user-friendly
  const formattedName = appName
    .replace(/^mobile/, '')  // Remove 'mobile' prefix
    .split(/(?=[A-Z])/).join(' ')  // Add spaces before capital letters
    .replace(/^\w/, c => c.toUpperCase());  // Capitalize first letter

  return (
    <div className="flex flex-col h-full">
      {/* Main display area */}
      <div className="flex-grow relative bg-gray-100 rounded-lg overflow-hidden mb-4">
        {selectedScreenshot ? (
          <div className="relative w-full h-full max-h-[70vh]">
            <Image
              src={selectedScreenshot}
              alt={`${formattedName} screenshot`}
              fill
              className="object-contain"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 80vw, 70vw"
            />
          </div>
        ) : (
          <div className="w-full h-64 flex items-center justify-center text-gray-400">
            No screenshot selected
          </div>
        )}
      </div>

      {/* Thumbnail gallery */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 mt-4">
        {screenshots.map((screenshot, index) => (
          <div 
            key={screenshot}
            className={`
              relative aspect-[9/16] cursor-pointer rounded-lg overflow-hidden border-2
              ${selectedScreenshot === screenshot ? 'border-blue-500' : 'border-transparent'}
              transition-all hover:opacity-90
            `}
            onClick={() => setSelectedScreenshot(screenshot)}
          >
            <Image
              src={screenshot}
              alt={`Thumbnail ${index + 1}`}
              fill
              className="object-contain"
              sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 16vw"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs py-1 px-2">
              {index + 1}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 