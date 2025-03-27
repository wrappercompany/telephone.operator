import { getArtifacts } from '../../utils/getArtifacts';
import ScreenshotGallery from '../../components/ScreenshotGallery';
import Link from 'next/link';
import { notFound } from 'next/navigation';

interface AppPageProps {
  params: {
    name: string;
  };
}

export default async function AppPage({ params }: AppPageProps) {
  const { name } = params;
  
  // Get all apps data
  const apps = await getArtifacts();
  
  // Find the current app
  const app = apps.find(app => app.name === name);
  
  // If app not found, show 404
  if (!app) {
    notFound();
  }
  
  // Format the app name to be more user-friendly
  const formattedName = name
    .replace(/^mobile/, '')  // Remove 'mobile' prefix
    .split(/(?=[A-Z])/).join(' ')  // Add spaces before capital letters
    .replace(/^\w/, c => c.toUpperCase());  // Capitalize first letter
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{formattedName}</h1>
          <p className="text-gray-600 mt-1">{app.screenshots.length} Screenshots</p>
        </div>
        
        <Link 
          href="/"
          className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded-md text-sm font-medium transition-colors"
        >
          Back to Apps
        </Link>
      </div>
      
      <hr className="border-gray-200" />
      
      <ScreenshotGallery screenshots={app.screenshots} appName={name} />
    </div>
  );
} 