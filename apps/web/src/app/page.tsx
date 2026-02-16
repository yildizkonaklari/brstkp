'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'
import Link from 'next/link'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function Home() {
    const { data: signal, isLoading } = useQuery({
        queryKey: ['top10', 'today'],
        queryFn: async () => {
            const res = await api.get('/signals/top10')
            return res.data
        }
    })

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Welcome back. Here is today's market overview.</p>
                </div>
                <div className="flex gap-2">
                    <Link href="/backtest">
                        <Button variant="outline">Run Backtest</Button>
                    </Link>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Market Regime</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {isLoading ? '...' : (signal?.regime || 'UNKNOWN')}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Based on XU100 Trend
                        </p>
                    </CardContent>
                </Card>

                {/* Placeholder Stats */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Active Symbols</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">482</div>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Today's Top 10</CardTitle>
                        <CardDescription>
                            Highest potential signals generated for {signal?.date || 'today'}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? <div>Loading...</div> : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[80px]">Rank</TableHead>
                                        <TableHead>Symbol</TableHead>
                                        <TableHead className="text-right">Score</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {signal?.top10?.map((item: any) => (
                                        <TableRow key={item.symbol}>
                                            <TableCell className="font-medium">{item.rank}</TableCell>
                                            <TableCell>{item.symbol}</TableCell>
                                            <TableCell className="text-right">{item.final_score?.toFixed(2)}</TableCell>
                                        </TableRow>
                                    )) || (
                                            <TableRow>
                                                <TableCell colSpan={3} className="text-center">No signals generated yet.</TableCell>
                                            </TableRow>
                                        )}
                                </TableBody>
                            </Table>
                        )}

                        {!isLoading && (!signal?.top10 || signal.top10.length === 0) && (
                            <div className="mt-4 p-4 border rounded-md bg-muted/50 text-sm">
                                No signals found. Try importing seed data or running the compute pipeline.
                                <br />
                                <Button
                                    variant="link"
                                    onClick={() => api.post('/data/compute?date_str=' + new Date().toISOString().split('T')[0])}
                                >
                                    Trigger Compute
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
