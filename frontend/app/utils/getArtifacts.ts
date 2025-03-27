import fs from 'fs';
import path from 'path';

interface ArtifactApp {
  name: string;
  screenshots: string[];
}

export async function getArtifacts(): Promise<ArtifactApp[]> {
  const artifactsDir = path.join(process.cwd(), '..', 'artifacts');
  
  // Get all app directories inside artifacts
  const appDirs = fs.readdirSync(artifactsDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
  
  const apps: ArtifactApp[] = [];
  
  for (const appDir of appDirs) {
    const screenshotsDir = path.join(artifactsDir, appDir, 'screenshots');
    
    if (fs.existsSync(screenshotsDir)) {
      const screenshots = fs.readdirSync(screenshotsDir)
        .filter(file => file.endsWith('.png')) // Only get PNG files
        .map(file => `/api/artifacts/${appDir}/screenshots/${file}`); // Path for API endpoint
      
      apps.push({
        name: appDir,
        screenshots
      });
    }
  }
  
  return apps;
} 