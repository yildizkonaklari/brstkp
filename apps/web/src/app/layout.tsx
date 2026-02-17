import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import Link from 'next/link'

export const metadata: Metadata = {
    title: 'BorsaTakip Analyst',
    description: 'BIST Stock Screener & Simulation',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body className="min-h-screen bg-background font-sans antialiased">
                <Providers>
                    <div className="min-h-screen flex flex-col">
                        <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                            <div className="container flex h-14 max-w-screen-2xl items-center">
                                <div className="mr-4 flex">
                                    <Link href="/" className="mr-6 flex items-center space-x-2 font-bold">
                                        BorsaTakip
                                    </Link>
                                    <nav className="flex items-center space-x-6 text-sm font-medium">
                                        <Link href="/top10" className="transition-colors hover:text-foreground/80 text-foreground/60">Top 10</Link>
                                        <Link href="/backtest" className="transition-colors hover:text-foreground/80 text-foreground/60">Backtest</Link>
                                        <Link href="/settings" className="transition-colors hover:text-foreground/80 text-foreground/60">Settings</Link>
                                    </nav>
                                </div>
                            </div>
                        </header>
                        <main className="flex-1 container py-6">
                            {children}
                        </main>
                    </div>
                </Providers>
            </body>
        </html>
    )
}
