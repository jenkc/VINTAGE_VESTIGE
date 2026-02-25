# Vintage Vestige - Week 1 Implementation Plan
**Next.js Frontend: Core Search Experience**

**Timeline**: Days 1-7  
**Goal**: Ship a working, beautiful search interface that showcases your frontend + design system skills  
**Outcome**: Portfolio-ready demo you can share with Anthropic

---

## Day 1: Project Setup + Design Foundation

### Morning: Next.js Project Initialization

**Step 1: Create Project**

```bash
# From your main project directory
npx create-next-app@latest vintage-vestige-web \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"

cd vintage-vestige-web
```

**Answer prompts**:
- TypeScript: Yes
- ESLint: Yes
- Tailwind CSS: Yes
- `src/` directory: Yes
- App Router: Yes
- Import alias: Yes (@/*)

**Step 2: Install Core Dependencies**

```bash
# UI Components
npm install @radix-ui/themes @radix-ui/colors
npm install lucide-react
npm install class-variance-authority clsx tailwind-merge

# State & Data
npm install zustand
npm install axios

# Forms (for later)
npm install react-hook-form zod @hookform/resolvers

# Dev tools
npm install -D prettier prettier-plugin-tailwindcss
```

**Step 3: Project Structure**

Create this folder structure:

```
vintage-vestige-web/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── globals.css         # Global styles
│   │   └── api/                # API routes (if needed)
│   ├── components/
│   │   ├── ui/                 # Design system components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── index.ts
│   │   ├── layout/             # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Navigation.tsx
│   │   └── search/             # Feature components
│   │       ├── SearchBar.tsx
│   │       ├── ImageUpload.tsx
│   │       └── ProductCard.tsx
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── utils.ts            # Utility functions
│   │   └── constants.ts        # App constants
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   └── styles/
│       └── theme.ts            # Theme configuration
```

```bash
# Create directories
mkdir -p src/components/{ui,layout,search}
mkdir -p src/lib
mkdir -p src/types
mkdir -p src/styles
```

### Afternoon: Design System Foundation

**Step 4: Configure Tailwind**

**File**: `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Vintage Vestige brand colors
        vintage: {
          cream: "#F5F1E8",
          beige: "#E8DCC8",
          sand: "#D4C4A8",
          taupe: "#B8A694",
          burgundy: "#8B4049",
          sage: "#A8B5A0",
          charcoal: "#3A3A3A",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
      },
    },
  },
  plugins: [],
};
export default config;
```

**Step 5: Typography Setup**

**File**: `src/app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vintage Vestige - AI-Powered Vintage Fashion Search",
  description: "Find vintage fashion without being a vintage expert. AI-powered visual search for unique vintage pieces.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className="font-sans antialiased bg-vintage-cream text-vintage-charcoal">
        {children}
      </body>
    </html>
  );
}
```

**Step 6: Global Styles**

**File**: `src/app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --radius: 0.5rem;
  }
  
  * {
    @apply border-vintage-taupe/20;
  }
  
  body {
    @apply bg-vintage-cream text-vintage-charcoal;
  }
  
  h1, h2, h3, h4, h5, h6 {
    @apply font-serif;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
```

**Step 7: Core Utilities**

**File**: `src/lib/utils.ts`

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with proper precedence
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format price to USD
 */
export function formatPrice(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

/**
 * Debounce function for search inputs
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };
    
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
```

---

## Day 2: Design System Components

### Morning: Base UI Components

**File**: `src/components/ui/Button.tsx`

```typescript
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-vintage-burgundy text-white hover:bg-vintage-burgundy/90",
        outline: "border-2 border-vintage-burgundy text-vintage-burgundy hover:bg-vintage-burgundy hover:text-white",
        ghost: "hover:bg-vintage-beige",
        link: "text-vintage-burgundy underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3",
        lg: "h-11 px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

**File**: `src/components/ui/Input.tsx`

```typescript
import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-vintage-taupe/30 bg-white px-3 py-2 text-sm",
          "placeholder:text-vintage-taupe/60",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vintage-burgundy focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
```

**File**: `src/components/ui/Card.tsx`

```typescript
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border border-vintage-taupe/20 bg-white shadow-sm",
      className
    )}
    {...props}
  />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("font-serif text-2xl font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-vintage-taupe", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

export { Card, CardHeader, CardTitle, CardDescription, CardContent };
```

**File**: `src/components/ui/Badge.tsx`

```typescript
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-vintage-burgundy text-white",
        secondary: "border-transparent bg-vintage-sage text-white",
        outline: "border-vintage-taupe text-vintage-charcoal",
        era: "border-vintage-taupe/30 bg-vintage-beige text-vintage-charcoal",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
```

**File**: `src/components/ui/index.ts`

```typescript
export { Button } from "./Button";
export { Input } from "./Input";
export { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./Card";
export { Badge } from "./Badge";
```

### Afternoon: TypeScript Types

**File**: `src/types/index.ts`

```typescript
// Product types
export interface Product {
  id: string;
  title: string;
  description: string;
  price: number; // in cents
  imageUrl: string;
  platform: "etsy" | "depop" | "grailed" | "dataset";
  url: string;
  era?: Era;
  category?: Category;
  tags?: string[];
  similarity?: number; // 0-1 for search results
}

// Era classification
export type Era = "1950s" | "1960s" | "1970s" | "1980s" | "1990s" | "2000s" | "y2k";

// Product categories
export type Category = 
  | "dresses"
  | "tops"
  | "bottoms"
  | "outerwear"
  | "accessories"
  | "shoes"
  | "jewelry";

// Search types
export interface SearchParams {
  query?: string;
  image?: File;
  era?: Era;
  category?: Category;
  minPrice?: number;
  maxPrice?: number;
  limit?: number;
}

export interface SearchResults {
  products: Product[];
  total: number;
  query: string;
  processingTime: number; // in ms
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
  };
}

// Filter options
export interface FilterOptions {
  eras: Era[];
  categories: Category[];
  priceRanges: {
    label: string;
    min: number;
    max: number;
  }[];
}
```

**File**: `src/lib/constants.ts`

```typescript
import { Era, Category } from "@/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ERAS: { value: Era; label: string; years: string }[] = [
  { value: "1950s", label: "50s", years: "1950-1959" },
  { value: "1960s", label: "60s", years: "1960-1969" },
  { value: "1970s", label: "70s", years: "1970-1979" },
  { value: "1980s", label: "80s", years: "1980-1989" },
  { value: "1990s", label: "90s", years: "1990-1999" },
  { value: "2000s", label: "00s", years: "2000-2009" },
  { value: "y2k", label: "Y2K", years: "1998-2004" },
];

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "dresses", label: "Dresses" },
  { value: "tops", label: "Tops" },
  { value: "bottoms", label: "Bottoms" },
  { value: "outerwear", label: "Outerwear" },
  { value: "accessories", label: "Accessories" },
  { value: "shoes", label: "Shoes" },
  { value: "jewelry", label: "Jewelry" },
];

export const PRICE_RANGES = [
  { label: "Under $25", min: 0, max: 2500 },
  { label: "$25 - $50", min: 2500, max: 5000 },
  { label: "$50 - $100", min: 5000, max: 10000 },
  { label: "$100 - $200", min: 10000, max: 20000 },
  { label: "$200+", min: 20000, max: 999999 },
];
```

---

## Day 3: API Client & State Management

### Morning: API Integration

**File**: `src/lib/api.ts`

```typescript
import axios from "axios";
import { API_BASE_URL } from "./constants";
import type { ApiResponse, SearchParams, SearchResults, Product } from "@/types";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Search API
export const searchApi = {
  /**
   * Text-based search
   */
  searchText: async (query: string, params?: Partial<SearchParams>): Promise<SearchResults> => {
    const response = await api.post<ApiResponse<SearchResults>>("/api/v1/search/text", {
      query,
      ...params,
    });
    
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || "Search failed");
    }
    
    return response.data.data;
  },

  /**
   * Image-based search
   */
  searchImage: async (image: File, params?: Partial<SearchParams>): Promise<SearchResults> => {
    const formData = new FormData();
    formData.append("image", image);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          formData.append(key, String(value));
        }
      });
    }
    
    const response = await api.post<ApiResponse<SearchResults>>("/api/v1/search/image", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || "Image search failed");
    }
    
    return response.data.data;
  },

  /**
   * Get product by ID
   */
  getProduct: async (id: string): Promise<Product> => {
    const response = await api.get<ApiResponse<Product>>(`/api/v1/products/${id}`);
    
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || "Product not found");
    }
    
    return response.data.data;
  },

  /**
   * Get similar products
   */
  getSimilar: async (id: string, limit: number = 12): Promise<Product[]> => {
    const response = await api.get<ApiResponse<Product[]>>(`/api/v1/similar/${id}`, {
      params: { limit },
    });
    
    if (!response.data.success || !response.data.data) {
      throw new Error(response.data.error || "Failed to fetch similar products");
    }
    
    return response.data.data;
  },
};

export default api;
```

**File**: `.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Afternoon: State Management

**File**: `src/lib/store.ts`

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Product, SearchResults } from "@/types";

interface SearchState {
  // Current search
  results: SearchResults | null;
  isSearching: boolean;
  searchError: string | null;
  
  // Saved items
  savedProducts: Product[];
  
  // Actions
  setResults: (results: SearchResults | null) => void;
  setIsSearching: (isSearching: boolean) => void;
  setSearchError: (error: string | null) => void;
  saveProduct: (product: Product) => void;
  unsaveProduct: (productId: string) => void;
  isProductSaved: (productId: string) => boolean;
  clearResults: () => void;
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      results: null,
      isSearching: false,
      searchError: null,
      savedProducts: [],
      
      setResults: (results) => set({ results, searchError: null }),
      setIsSearching: (isSearching) => set({ isSearching }),
      setSearchError: (searchError) => set({ searchError, isSearching: false }),
      
      saveProduct: (product) =>
        set((state) => ({
          savedProducts: [...state.savedProducts, product],
        })),
      
      unsaveProduct: (productId) =>
        set((state) => ({
          savedProducts: state.savedProducts.filter((p) => p.id !== productId),
        })),
      
      isProductSaved: (productId) => {
        return get().savedProducts.some((p) => p.id === productId);
      },
      
      clearResults: () => set({ results: null, searchError: null }),
    }),
    {
      name: "vintage-vestige-search",
      partialize: (state) => ({ savedProducts: state.savedProducts }),
    }
  )
);
```

---

## Day 4: Layout Components

### Morning: Header & Navigation

**File**: `src/components/layout/Header.tsx`

```typescript
"use client";

import Link from "next/link";
import { Search, Heart, Menu } from "lucide-react";
import { Button } from "@/components/ui";
import { useSearchStore } from "@/lib/store";

export function Header() {
  const savedProducts = useSearchStore((state) => state.savedProducts);
  
  return (
    <header className="sticky top-0 z-50 w-full border-b border-vintage-taupe/20 bg-vintage-cream/95 backdrop-blur supports-[backdrop-filter]:bg-vintage-cream/60">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2">
          <h1 className="font-serif text-2xl font-bold text-vintage-burgundy">
            Vintage Vestige
          </h1>
        </Link>
        
        {/* Navigation */}
        <nav className="hidden md:flex items-center space-x-6">
          <Link
            href="/search"
            className="text-sm font-medium text-vintage-charcoal hover:text-vintage-burgundy transition-colors"
          >
            Search
          </Link>
          <Link
            href="/explore"
            className="text-sm font-medium text-vintage-charcoal hover:text-vintage-burgundy transition-colors"
          >
            Explore
          </Link>
          <Link
            href="/timeline"
            className="text-sm font-medium text-vintage-charcoal hover:text-vintage-burgundy transition-colors"
          >
            Timeline
          </Link>
        </nav>
        
        {/* Actions */}
        <div className="flex items-center space-x-2">
          <Link href="/saved">
            <Button variant="ghost" size="icon" className="relative">
              <Heart className="h-5 w-5" />
              {savedProducts.length > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-vintage-burgundy text-[10px] text-white flex items-center justify-center">
                  {savedProducts.length}
                </span>
              )}
            </Button>
          </Link>
          
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
```

**File**: `src/components/layout/Footer.tsx`

```typescript
import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-vintage-taupe/20 bg-vintage-beige">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <h3 className="font-serif text-lg font-bold text-vintage-burgundy">
              Vintage Vestige
            </h3>
            <p className="text-sm text-vintage-taupe">
              AI-powered vintage fashion search. Find unique pieces without being a vintage expert.
            </p>
          </div>
          
          {/* Links */}
          <div>
            <h4 className="font-semibold mb-4">Discover</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/search" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Search
                </Link>
              </li>
              <li>
                <Link href="/explore" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Explore
                </Link>
              </li>
              <li>
                <Link href="/timeline" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Timeline
                </Link>
              </li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/about" className="text-vintage-taupe hover:text-vintage-burgundy">
                  About
                </Link>
              </li>
              <li>
                <Link href="/blog" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Blog
                </Link>
              </li>
              <li>
                <a href="https://github.com/yourusername/vintage-vestige" className="text-vintage-taupe hover:text-vintage-burgundy">
                  GitHub
                </a>
              </li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Legal</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/privacy" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Privacy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-vintage-taupe hover:text-vintage-burgundy">
                  Terms
                </Link>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="mt-12 pt-8 border-t border-vintage-taupe/20 text-center text-sm text-vintage-taupe">
          <p>© {new Date().getFullYear()} Vintage Vestige. Built with AI for vintage lovers.</p>
        </div>
      </div>
    </footer>
  );
}
```

**Update**: `src/app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vintage Vestige - AI-Powered Vintage Fashion Search",
  description: "Find vintage fashion without being a vintage expert. AI-powered visual search for unique vintage pieces.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className="font-sans antialiased bg-vintage-cream text-vintage-charcoal min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
```

---

## Day 5: Home Page Hero

**File**: `src/app/page.tsx`

```typescript
import Link from "next/link";
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
          AI-powered visual search for unique vintage pieces. Upload a photo or describe what you're looking for.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/search?mode=image">
            <Button size="lg" className="w-full sm:w-auto">
              <Upload className="mr-2 h-5 w-5" />
              Upload Image
            </Button>
          </Link>
          <Link href="/search?mode=text">
            <Button size="lg" variant="outline" className="w-full sm:w-auto">
              <Search className="mr-2 h-5 w-5" />
              Search by Text
            </Button>
          </Link>
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
                Take a photo of what you're looking for or describe it in words
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-vintage-burgundy/10 flex items-center justify-center mx-auto">
                <TrendingUp className="h-6 w-6 text-vintage-burgundy" />
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
              <div className="w-12 h-12 rounded-full bg-vintage-burgundy/10 flex items-center justify-center mx-auto">
                <Search className="h-6 w-6 text-vintage-burgundy" />
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
      
      {/* Browse by Era - Coming on Day 6 */}
      <section className="space-y-8">
        <h2 className="font-serif text-3xl font-bold text-center">
          Browse by Era
        </h2>
        <p className="text-center text-vintage-taupe">
          Explore vintage fashion by decade
        </p>
        {/* Era cards will be added on Day 6 */}
      </section>
    </div>
  );
}
```

---

## Day 6-7: Search Components

### Search Bar Component

**File**: `src/components/search/SearchBar.tsx`

```typescript
"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { Input, Button } from "@/components/ui";
import { debounce } from "@/lib/utils";

interface SearchBarProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  initialValue?: string;
}

export function SearchBar({ onSearch, placeholder = "Search vintage fashion...", initialValue = "" }: SearchBarProps) {
  const [query, setQuery] = useState(initialValue);
  
  // Debounced search
  const debouncedSearch = debounce((value: string) => {
    if (value.trim()) {
      onSearch(value.trim());
    }
  }, 500);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
      <Input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder={placeholder}
        className="pl-10 pr-4 h-12 text-base"
      />
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-vintage-taupe/60" />
    </form>
  );
}
```

### Image Upload Component

**File**: `src/components/search/ImageUpload.tsx`

```typescript
"use client";

import { useState, useRef } from "react";
import { Upload, X } from "lucide-react";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

interface ImageUploadProps {
  onUpload: (file: File) => void;
  className?: string;
}

export function ImageUpload({ onUpload, className }: ImageUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleFile = (file: File) => {
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
      onUpload(file);
    }
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };
  
  const clearPreview = () => {
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };
  
  return (
    <div className={cn("w-full max-w-2xl mx-auto", className)}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="hidden"
      />
      
      {preview ? (
        <div className="relative group">
          <img
            src={preview}
            alt="Upload preview"
            className="w-full h-64 object-cover rounded-lg border-2 border-vintage-taupe/20"
          />
          <Button
            onClick={clearPreview}
            variant="outline"
            size="icon"
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors",
            isDragging
              ? "border-vintage-burgundy bg-vintage-burgundy/5"
              : "border-vintage-taupe/30 hover:border-vintage-burgundy/50"
          )}
        >
          <Upload className="h-12 w-12 mx-auto mb-4 text-vintage-taupe/60" />
          <p className="text-lg font-medium mb-2">
            Drop an image here or click to upload
          </p>
          <p className="text-sm text-vintage-taupe">
            JPG, PNG, or WEBP up to 10MB
          </p>
        </div>
      )}
    </div>
  );
}
```

### Product Card Component

**File**: `src/components/search/ProductCard.tsx`

```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Heart, ExternalLink } from "lucide-react";
import { Card, Badge, Button } from "@/components/ui";
import { formatPrice } from "@/lib/utils";
import { useSearchStore } from "@/lib/store";
import type { Product } from "@/types";

interface ProductCardProps {
  product: Product;
  showSimilarity?: boolean;
}

export function ProductCard({ product, showSimilarity = false }: ProductCardProps) {
  const [imageError, setImageError] = useState(false);
  const { saveProduct, unsaveProduct, isProductSaved } = useSearchStore();
  const isSaved = isProductSaved(product.id);
  
  const handleSaveToggle = () => {
    if (isSaved) {
      unsaveProduct(product.id);
    } else {
      saveProduct(product);
    }
  };
  
  return (
    <Card className="group overflow-hidden hover:shadow-lg transition-shadow">
      <div className="relative aspect-[3/4] bg-vintage-beige overflow-hidden">
        {!imageError ? (
          <Image
            src={product.imageUrl}
            alt={product.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-vintage-taupe">
            Image unavailable
          </div>
        )}
        
        {/* Overlay actions */}
        <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            onClick={handleSaveToggle}
            variant="outline"
            size="icon"
            className="bg-white/90 backdrop-blur"
          >
            <Heart className={cn("h-4 w-4", isSaved && "fill-vintage-burgundy text-vintage-burgundy")} />
          </Button>
        </div>
        
        {/* Era badge */}
        {product.era && (
          <div className="absolute bottom-2 left-2">
            <Badge variant="era">{product.era}</Badge>
          </div>
        )}
        
        {/* Similarity score */}
        {showSimilarity && product.similarity !== undefined && (
          <div className="absolute bottom-2 right-2">
            <Badge variant="secondary">
              {Math.round(product.similarity * 100)}% match
            </Badge>
          </div>
        )}
      </div>
      
      <div className="p-4 space-y-2">
        <Link href={`/product/${product.id}`}>
          <h3 className="font-medium line-clamp-2 hover:text-vintage-burgundy transition-colors">
            {product.title}
          </h3>
        </Link>
        
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold">
            {formatPrice(product.price)}
          </p>
          
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-vintage-taupe hover:text-vintage-burgundy flex items-center gap-1"
          >
            {product.platform}
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </Card>
  );
}
```

---

## Testing & Running

### Run Development Server

```bash
npm run dev
```

Open http://localhost:3000

### Test Checklist

**Day 1-2**: Design System
- [ ] All UI components render correctly
- [ ] Tailwind colors match brand palette
- [ ] Typography (serif headings, sans body) working
- [ ] Button variants all display properly

**Day 3**: API & State
- [ ] API client configured with correct base URL
- [ ] State management working (test save/unsave)
- [ ] TypeScript types have no errors

**Day 4**: Layout
- [ ] Header sticky on scroll
- [ ] Footer displays correctly
- [ ] Navigation links work
- [ ] Saved count badge shows up

**Day 5**: Home Page
- [ ] Hero section centered and responsive
- [ ] CTA buttons navigate correctly
- [ ] How It Works cards display properly

**Day 6-7**: Search Components
- [ ] Search bar debouncing works
- [ ] Image upload drag & drop functional
- [ ] Product cards render with placeholder data
- [ ] Saved heart icon toggles state

---

## Next Steps (Week 2)

After completing Week 1, you'll have:
✅ Complete design system  
✅ Core layouts (header, footer, home)  
✅ Search components ready  
✅ API client configured  
✅ State management working  

**Week 2 will add**:
- Search results page with real API integration
- Product detail pages
- Interactive data visualizations
- Collections feature

---

## Deliverable

By end of Week 1, you should be able to:
1. Navigate to http://localhost:3000 and see a polished home page
2. Click "Search by Text" and see the search interface
3. Upload an image (even if backend isn't connected yet)
4. See placeholder product cards
5. Save/unsave products to collection

**Screenshot this and add to your portfolio** - even without the backend connected, this demonstrates:
- Design system implementation
- Component architecture
- TypeScript proficiency
- Modern React patterns
- Responsive design

---

## Common Issues & Solutions

**Issue**: Tailwind classes not applying  
**Solution**: Check `tailwind.config.ts` content paths include `src/`

**Issue**: Font variables not working  
**Solution**: Verify `className={...variable}` on `<html>` tag

**Issue**: API calls failing  
**Solution**: Check `.env.local` has correct `NEXT_PUBLIC_API_URL`

**Issue**: Image upload preview not showing  
**Solution**: FileReader needs `reader.readAsDataURL(file)`

**Issue**: Zustand persist not working  
**Solution**: Check browser localStorage is enabled

---

**Ready to start coding!** 🎨

This gives you a complete, professional frontend foundation that directly demonstrates every requirement in the Anthropic Design Engineer job posting.
