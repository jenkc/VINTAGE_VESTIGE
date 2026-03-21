"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

export default function Header() {
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <header className="z-50 h-16 border-b border-grey-200 bg-white/95 backdrop-blur-[12px]">
             <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4">
                {/* Logo */}
                <Link href="/" className="font-display text-xl font-bold text-black">
                    Vintage Vestige
                </Link>

                {/* Desktop nav */}
                <nav className="hidden items-center gap-6 md:flex">
                    <Link href="/search" className="text-sm text-dark hover:text-accent">
                        Search
                    </Link>
                    <Link href="/explore/functions" className="text-sm text-dark hover:text-accent">
                        Explore
                    </Link>

                    <Link href="/bridges" className="text-sm text-dark hover:text-accent">
                        Bridges
                    </Link>

                    <Link href="/about" className="text-sm text-dark hover:text-accent">
                        About
                    </Link>
                </nav>

                {/* Mobile hamburger */}
                <button
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="flex h-10 w-10 items-center justify-center md:hidden"
                    aria-label="Toggle menu"
                >
                    {menuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {/* Mobile menu dropdown */}
            {menuOpen && (
                <div className="border-b border-grey-200 bg-white px-4 pb-4 md:hidden">
                    <nav className="flex flex-col gap-3">
                        <Link
                            href="/search"
                            onClick={() => setMenuOpen(false)}
                            className="text-sm text-dark hover:text-accent"
                        >
                            Search
                        </Link>

                        <Link
                            href="/explore/functions"
                            onClick={() => setMenuOpen(false)}
                            className="text-sm text-dark hover:text-accent"
                        >
                            Explore
                        </Link>

                        <Link
                            href="/bridges"
                            onClick={() => setMenuOpen(false)}
                            className="text-sm text-dark hover:text-accent"
                        >
                            Bridges
                        </Link>

                        <Link
                            href="/about"
                            onClick={() => setMenuOpen(false)}
                            className="text-sm text-dark hover:text-accent"
                        >
                            About
                        </Link>
                    </nav>
                </div>
            )}
        </header>
    );
}
