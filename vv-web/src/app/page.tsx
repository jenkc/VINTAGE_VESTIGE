import { Search, Upload, TrendingUp } from "lucide-react";
import { Button, Card, CardContent } from "@/components/ui";

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-12 space-y-20">
      {/* Hero Section */}
      <section className="text-center space-y-8 py-12">
        <h1 className="font-serif text-5xl md:text-7xl font-bold text-vintage-charcoal text-balance">
          Find vintage fashion without being a{" "}
          <span className="text-vintage-burgundy">vintage expert</span>
        </h1>

        <p className="text-xl text-vintage-taupe max-w-2xl mx-auto text-balance">
          AI-powered visual search for unique vintage pieces. Upload a photo or
          describe what you&apos;re looking for.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" className="w-full sm:w-auto">
            <Upload className="mr-2 h-5 w-5" />
            Upload Image
          </Button>
          <Button size="lg" variant="outline" className="w-full sm:w-auto border-vintage-caerulean text-vintage-caerulean hover:bg-vintage-caerulean hover:text-white">
            <Search className="mr-2 h-5 w-5" />
            Search by Text
          </Button>
        </div>
      </section>

      {/* How It Works */}
      <section className="space-y-8">
        <h2 className="font-serif text-3xl font-bold text-center">
          How It Works
        </h2>

        <div className="grid md:grid-cols-3 gap-6">
          <Card>
            <CardContent className="pt-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-vintage-burgundy/10 flex items-center justify-center mx-auto">
                <Upload className="h-6 w-6 text-vintage-burgundy" />
              </div>
              <h3 className="font-serif text-xl font-semibold">
                1. Upload or Describe
              </h3>
              <p className="text-vintage-taupe">
                Take a photo of what you&apos;re looking for or describe it in
                words
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-vintage-caerulean/10 flex items-center justify-center mx-auto">
                <TrendingUp className="h-6 w-6 text-vintage-caerulean" />
              </div>
              <h3 className="font-serif text-xl font-semibold">
                2. AI Analyzes
              </h3>
              <p className="text-vintage-taupe">
                Our AI understands style, era, and visual similarity
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-vintage-lilac/10 flex items-center justify-center mx-auto">
                <Search className="h-6 w-6 text-vintage-lilac" />
              </div>
              <h3 className="font-serif text-xl font-semibold">
                3. Find Matches
              </h3>
              <p className="text-vintage-taupe">
                Get visually similar vintage pieces from across the web
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Browse by Era */}
      <section className="space-y-8 rounded-2xl bg-vintage-navy/5 p-12">
        <h2 className="font-serif text-3xl font-bold text-center">
          Browse by <span className="text-vintage-caerulean">Era</span>
        </h2>
        <p className="text-center text-vintage-taupe">
          Explore vintage fashion by decade
        </p>
      </section>
    </div>
  );
}
