import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto max-w-7xl px-4">
        {/* Mobile: single column stack / Desktop: 3-column grid */}
        <div className="grid gap-8 md:grid-cols-3">
          {/* Brand */}
          <div>
            <h3 className="text-lg font-bold">Vintage Vestige</h3>
            <p className="mt-2 text-sm text-charcoal-soft">
              Bridging fashion across centuries through AI-powered style connections.
            </p>
          </div>

          {/* Nav links */}
          <div>
            <h4 className="text-sm font-semibold uppercase tracking-wider text-muted">
              Explore
            </h4>
            <nav className="mt-3 flex flex-col gap-2">
              <Link href="/search" className="text-sm text-charcoal-soft hover:text-terracotta">
                Search
              </Link>
              <Link href="/about" className="text-sm text-charcoal-soft hover:text-terracotta">
                About
              </Link>
            </nav>
          </div>

          {/* Built with */}
          <div>
            <h4 className="text-sm font-semibold uppercase tracking-wider text-muted">
              Built With
            </h4>
            <p className="mt-3 text-sm text-charcoal-soft">
              Next.js, FastAPI, Qdrant, and Claude AI
            </p>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-8 border-t border-border pt-8 text-center text-sm text-muted">
          &copy; {new Date().getFullYear()} Vintage Vestige
        </div>
      </div>
    </footer>
  );
}
