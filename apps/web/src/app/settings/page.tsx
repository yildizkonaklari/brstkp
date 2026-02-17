'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'
import { Loader2, RefreshCw, PlayIcon } from 'lucide-react'

export default function SettingsPage() {
    const [isLoading, setIsLoading] = useState(false)
    const [isComputing, setIsComputing] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [error, setError] = useState<string | null>(null)

    const handleUpdateData = async () => {
        setIsLoading(true)
        setResult(null)
        setError(null)
        try {
            // Call the backend API to start the import process
            // Defaulting to 365 days lookback
            const response = await api.post('/data/import/yahoo', null, {
                params: { days: 365 }
            })
            setResult(response.data)
        } catch (err: any) {
            console.error(err)
            setError(err.response?.data?.detail || "Failed to update data. Ensure API is running.")
        } finally {
            setIsLoading(false)
        }
    }

    const handleCompute = async () => {
        setIsComputing(true)
        setResult(null)
        setError(null)
        try {
            const today = new Date().toISOString().split('T')[0]
            const response = await api.post('/data/compute', null, {
                params: { date_str: today }
            })
            setResult({ message: "Analysis Complete: " + JSON.stringify(response.data) }) // Simple display
        } catch (err: any) {
            console.error(err)
            setError(err.response?.data?.detail || "Analysis failed.")
        } finally {
            setIsComputing(false)
        }
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

            {/* Data Management Section */}
            <Card>
                <CardHeader>
                    <CardTitle>Data Management</CardTitle>
                    <CardDescription>Manage market data updates and synchronization.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                            <div className="font-medium flex items-center gap-2">
                                <RefreshCw className="h-4 w-4 text-muted-foreground" />
                                Update Market Data (Yahoo Finance)
                            </div>
                            <div className="text-sm text-muted-foreground mt-1">
                                Fetch latest daily OHLCV data for all tracked symbols. This may take a few minutes.
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                onClick={handleUpdateData}
                                disabled={isLoading || isComputing}
                            >
                                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {isLoading ? "Updating..." : "Update Now"}
                            </Button>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                            <div className="font-medium flex items-center gap-2">
                                <PlayIcon className="h-4 w-4 text-muted-foreground" />
                                Trigger Analysis Pipeline
                            </div>
                            <div className="text-sm text-muted-foreground mt-1">
                                Re-run feature engineering and scoring for today ({new Date().toISOString().split('T')[0]}).
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                onClick={handleCompute}
                                disabled={isLoading || isComputing}
                                variant="secondary"
                            >
                                {isComputing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {isComputing ? "Computing..." : "Run Analysis"}
                            </Button>
                        </div>
                    </div>

                    {error && (
                        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
                            Error: {error}
                        </div>
                    )}

                    {result && (
                        <div className="p-4 bg-green-500/10 text-green-700 dark:text-green-400 rounded-lg text-sm space-y-2 border border-green-500/20">
                            <div className="font-semibold">Update Successful</div>
                            <div>{result.message}</div>
                            {result.index_status && (
                                <div className="text-xs opacity-80">Index Status: {result.index_status}</div>
                            )}

                            {result.debug_errors && result.debug_errors.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-green-500/20">
                                    <div className="font-semibold text-xs mb-1">Warnings/Errors ({result.debug_errors.length}):</div>
                                    <ul className="list-disc pl-4 max-h-32 overflow-y-auto space-y-1">
                                        {result.debug_errors.map((e: string, i: number) => (
                                            <li key={i} className="text-xs">{e}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>System Configuration</CardTitle>
                    <CardDescription>Global parameters for the analysis engine.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                            <div className="font-medium">Market Regime Override</div>
                            <div className="text-sm text-muted-foreground">Force Risk ON/OFF behavior regardless of index trend.</div>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" disabled>Auto (Default)</Button>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                            <div className="font-medium">Stop Loss Multiplier</div>
                            <div className="text-sm text-muted-foreground">ATR multiplier for trailing stops.</div>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline">2.0x</Button>
                        </div>
                    </div>

                    <div className="p-4 bg-muted/50 rounded text-sm">
                        Note: Settings persistence is not implemented in this MVP demo.
                        Parameters are hardcoded in the backend configuration or passed dynamically in Backtest.
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
