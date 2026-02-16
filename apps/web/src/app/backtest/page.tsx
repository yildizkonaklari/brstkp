'use client'

import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import api from '@/lib/api'
import { useState } from 'react'
import Link from 'next/link'

export default function BacktestPage() {
    const [params, setParams] = useState({
        start_date: '2023-01-01',
        end_date: '2023-06-01',
        initial_capital: 100000
    })

    const [lastRunId, setLastRunId] = useState<string | null>(null)

    const mutation = useMutation({
        mutationFn: async (data: any) => {
            const res = await api.post('/backtest/run', data)
            return res.data
        },
        onSuccess: (data) => {
            setLastRunId(data.run_id)
        }
    })

    // Polling for status if running?
    const { data: result } = useQuery({
        queryKey: ['backtest', lastRunId],
        queryFn: async () => {
            if (!lastRunId) return null
            const res = await api.get(`/backtest/${lastRunId}`)
            return res.data
        },
        enabled: !!lastRunId,
        refetchInterval: (query) => {
            const data = query.state.data as any
            return (data?.status === 'PENDING' || data?.status === 'RUNNING') ? 1000 : false
        }
    })

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Backtest Simulation</h1>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>New Simulation</CardTitle>
                        <CardDescription>Configure parameters to run a historical test.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid gap-2">
                            <label className="text-sm font-medium">Start Date</label>
                            <input
                                type="date"
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={params.start_date}
                                onChange={e => setParams({ ...params, start_date: e.target.value })}
                            />
                        </div>
                        <div className="grid gap-2">
                            <label className="text-sm font-medium">End Date</label>
                            <input
                                type="date"
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                value={params.end_date}
                                onChange={e => setParams({ ...params, end_date: e.target.value })}
                            />
                        </div>

                        <Button
                            className="w-full"
                            onClick={() => mutation.mutate(params)}
                            disabled={mutation.isPending}
                        >
                            {mutation.isPending ? 'Starting...' : 'Run Backtest'}
                        </Button>
                    </CardContent>
                </Card>

                {lastRunId && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Run Status: {result?.status || 'Loading...'}</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {result?.status === 'COMPLETED' ? (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 bg-muted rounded-lg">
                                            <div className="text-sm text-muted-foreground">CAGR</div>
                                            <div className="text-2xl font-bold">{result.metrics?.cagr}%</div>
                                        </div>
                                        <div className="p-4 bg-muted rounded-lg">
                                            <div className="text-sm text-muted-foreground">Max Drawdown</div>
                                            <div className="text-2xl font-bold text-destructive">{result.metrics?.max_dd}%</div>
                                        </div>
                                    </div>

                                    <h3 className="font-semibold">Recent Trades</h3>
                                    <div className="max-h-[200px] overflow-auto border rounded-md">
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>Date</TableHead>
                                                    <TableHead>Symbol</TableHead>
                                                    <TableHead>Action</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {result.trades.slice(0, 10).map((t: any, i: number) => (
                                                    <TableRow key={i}>
                                                        <TableCell>{t.date}</TableCell>
                                                        <TableCell>{t.symbol}</TableCell>
                                                        <TableCell className={t.action === 'BUY' ? 'text-green-500' : 'text-red-500'}>{t.action}</TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </div>
                                </div>
                            ) : (
                                <div>Processing... please wait.</div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    )
}
