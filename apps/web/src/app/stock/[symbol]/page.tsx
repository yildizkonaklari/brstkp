'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'
import { useParams } from 'next/navigation'
import Link from 'next/link'

export default function StockDetailPage() {
    const params = useParams()
    const symbol = typeof params.symbol === 'string' ? params.symbol : ''

    const { data: scores, isLoading } = useQuery({
        queryKey: ['stock', symbol],
        queryFn: async () => {
            if (!symbol) return []
            const res = await api.get(`/signals/stock/${symbol}`)
            return res.data
        },
        enabled: !!symbol
    })

    // Get most recent
    const latest = scores && scores.length > 0 ? scores[0] : null

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Link href="/top10"><Button variant="ghost">← Back</Button></Link>
                <h1 className="text-3xl font-bold tracking-tight">{symbol} Analysis</h1>
            </div>

            {latest && (
                <div className="grid gap-4 md:grid-cols-3">
                    <Card>
                        <CardHeader><CardTitle>Final Score</CardTitle></CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-primary">{latest.final_score?.toFixed(2)}</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader><CardTitle>Potential</CardTitle></CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-green-500">{latest.potential_score?.toFixed(2)}</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader><CardTitle>Risk</CardTitle></CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-red-500">{latest.risk_score?.toFixed(2)}</div>
                        </CardContent>
                    </Card>
                </div>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Score History</CardTitle>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Final</TableHead>
                                <TableHead>Potential</TableHead>
                                <TableHead>Risk</TableHead>
                                <TableHead>Explain</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {scores?.map((s: any) => (
                                <TableRow key={s.date}>
                                    <TableCell>{s.date}</TableCell>
                                    <TableCell className="font-bold">{s.final_score?.toFixed(2)}</TableCell>
                                    <TableCell className="text-green-600">{s.potential_score?.toFixed(2)}</TableCell>
                                    <TableCell className="text-red-600">{s.risk_score?.toFixed(2)}</TableCell>
                                    <TableCell className="text-xs text-muted-foreground w-[40%]">
                                        {s.explain_json ? JSON.stringify(s.explain_json) : '-'}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
