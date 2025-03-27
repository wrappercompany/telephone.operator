import { getArtifacts } from './utils/getArtifacts';
import AppCard from './components/AppCard';

export default async function Home() {
  const apps = await getArtifacts();

  return (
    <div className="container mx-auto px-4 py-12 bg-[#fafafa]">
      {apps.length === 0 ? (
        <div className="text-center py-12">
          <h2 className="text-xl text-gray-500">No apps found</h2>
          <p className="mt-2 text-gray-400">Check the artifacts directory to make sure it contains app screenshots.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
          {apps.map((app) => (
            <AppCard key={app.name} name={app.name} screenshots={app.screenshots} />
          ))}
        </div>
      )}
    </div>
  );
}
