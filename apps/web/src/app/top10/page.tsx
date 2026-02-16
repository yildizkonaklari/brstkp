'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import api from '@/lib/api'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function Top10Page() {
    const { data: signal, isLoading } = useQuery({
        queryKey: ['top10', 'today'],
        queryFn: async () => {
            const res = await api.get('/signals/top10')
            return res.data
        }
    })

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Top 10 Signals</h1>

            <Card>
                <CardHeader>
                    <CardTitle>Daily Ranking</CardTitle>
                    <CardDescription>
                        Date: {signal?.date} | Regime: {signal?.regime}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[100px]">Rank</TableHead>
                                <TableHead>Symbol</TableHead>
                                <TableHead>Score</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {signal?.top10?.map((item: any) => (
                                <TableRow key={item.symbol}>
                                    <TableCell className="font-bold text-lg">#{item.rank}</TableCell>
                                    <TableCell className="font-medium text-lg text-primary">{item.symbol}</TableCell>
                                    <TableCell>{item.final_score?.toFixed(2)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
