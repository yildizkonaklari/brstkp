'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function SettingsPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

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
