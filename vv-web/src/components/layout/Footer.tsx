import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-black text-white px-6 py-16 md:px-12">
      <div className="mx-auto max-w-[1200px] grid gap-12 md:grid-cols-3">
        {/* Brand */}
        <div>
          <h3 className="font-display text-[13px] font-bold uppercase tracking-[0.2em]">
            Vintage Vestige
          </h3>
          <p className="mt-4 font-editorial text-lg italic leading-[1.5] text-white/60">
            &ldquo;Start from a question,<br />not a timeline.&rdquo;
          </p>
        </div>

        {/* Navigate */}
        <div>
          <h4 className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40">
            Navigate
          </h4>
          <nav className="mt-5 flex flex-col gap-2.5">
            <Link href="/search" className="text-sm text-white/70 hover:text-white transition-colors">
              Search
            </Link>
            <Link href="/explore/functions" className="text-sm text-white/70 hover:text-white transition-colors">
              Explore
            </Link>
            <Link href="/bridges" className="text-sm text-white/70 hover:text-white transition-colors">
              Connections
            </Link>
            <Link href="/about" className="text-sm text-white/70 hover:text-white transition-colors">
              About
            </Link>
          </nav>
        </div>

        {/* Collection stats */}
        <div>
          <h4 className="font-mono text-[10px] uppercase tracking-[0.15em] text-white/40">
            Collection
          </h4>
          <div className="mt-5 flex flex-col gap-4">
            <div>
              <span className="text-[32px] font-bold">3,100+</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.1em] text-white/40">Garments</span>
            </div>
            <div>
              <span className="text-[32px] font-bold">19,000+</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.1em] text-white/40">Connections</span>
            </div>
            <div>
              <span className="text-[32px] font-bold">500+</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.1em] text-white/40">Years</span>
            </div>
          </div>
        </div>
      </div>

      {/* Built with */}
      <div className="mx-auto max-w-[1200px] mt-12 pt-8 border-t border-white/10">
        <p className="font-mono text-[10px] uppercase tracking-[0.1em] text-white/30">
          Built with Next.js, FastAPI, pgvector, and Claude AI
        </p>
        <p className="mt-2 font-mono text-[10px] text-white/20">
          &copy; {new Date().getFullYear()} Vintage Vestige
        </p>
      </div>
    </footer>
  );
}
