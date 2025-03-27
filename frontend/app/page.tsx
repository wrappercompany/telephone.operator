import { getArtifacts } from './utils/getArtifacts';
import AppCard from './components/AppCard';

export default async function Home() {
  const apps = await getArtifacts();

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-bold mb-6">App Screenshots Gallery</h1>
        <p className="text-gray-600 mb-4">
          View and explore screenshots from various apps. Click on an app to see all its screenshots.
        </p>
      </section>

      {apps.length === 0 ? (
        <div className="text-center py-12">
          <h2 className="text-xl text-gray-500">No apps found</h2>
          <p className="mt-2 text-gray-400">Check the artifacts directory to make sure it contains app screenshots.</p>
        </div>
      ) : (
        <section>
          <h2 className="text-xl font-semibold mb-4">Available Apps</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {apps.map((app) => (
              <AppCard key={app.name} name={app.name} screenshots={app.screenshots} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
